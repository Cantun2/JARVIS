"""HERMES — triage des mails.

Classification par règles (rôle du modèle local / des règles apprises que l'utilisateur
contrôle) + résumé une ligne via l'InferenceGateway. Ne rédige rien d'envoyé, ne dispose
JAMAIS de MAIL_SEND.
"""

from __future__ import annotations

import asyncio
from collections import Counter

from pydantic import BaseModel

from jarvis.agents.base import JarvisAgent
from jarvis.agents.mocks.mail_fixtures import VIP_SENDERS
from jarvis.core.context import AgentContext
from jarvis.core.contracts import (
    AgentContract,
    AgentInput,
    AgentOutput,
    Budget,
    Permission,
)
from jarvis.core.events import EventType
from jarvis.inference.gateway import InferenceGateway
from jarvis.inference.types import ChatMessage
from jarvis.io.mail import Mail

# Catégories, de la plus prioritaire à la moins.
CATEGORY_PRIORITY = {"urgent": 100, "action": 70, "info": 40, "newsletter": 20, "spam": 0}

_URGENT_KW = ("urgent", "asap", "deadline", "immédiat", "bloquant", "avant 12h", "ce soir")
_ACTION_KW = ("peux-tu", "pouvez-vous", "merci de valider", "action requise", "confirmer", "?")
_NEWSLETTER_HINT = ("newsletter", "no-reply", "noreply", "mailchimp", "désabonn")
_SPAM_KW = ("gagné", "loterie", "viagra", "click here", "félicitations vous avez")


def _fallback_summary(mail: Mail) -> str:
    """Résumé déterministe sans modèle (repli quand l'inférence est lente/absente)."""
    text = " ".join(mail.subject.split())
    if not text:
        return "(sans objet)"
    return text[:117] + "…" if len(text) > 120 else text


def _fallback_draft(mail: Mail) -> str:
    """Brouillon déterministe sans modèle (accusé de réception poli)."""
    subject = " ".join(mail.subject.split()) or "votre message"
    return (
        f"Bonjour,\n\nMerci pour « {subject} ». Je reviens vers vous rapidement.\n\n"
        "Bien cordialement,\nQuentin"
    )


def classify(mail: Mail, overrides: dict[str, str] | None = None) -> tuple[str, int]:
    """Retourne (catégorie, priorité). Déterministe.

    Les règles **apprises** (`overrides` : expéditeur → catégorie, corrigées par
    l'utilisateur dans l'UI) priment sur les règles par défaut.
    """
    if overrides and mail.sender in overrides:
        category = overrides[mail.sender]
        return category, CATEGORY_PRIORITY.get(category, CATEGORY_PRIORITY["info"])

    text = f"{mail.subject}\n{mail.body}".lower()
    sender = mail.sender.lower()

    if any(k in text for k in _SPAM_KW):
        return "spam", CATEGORY_PRIORITY["spam"]
    if mail.sender in VIP_SENDERS or any(k in text for k in _URGENT_KW):
        return "urgent", CATEGORY_PRIORITY["urgent"]
    if any(h in sender for h in _NEWSLETTER_HINT) or any(h in text for h in _NEWSLETTER_HINT):
        return "newsletter", CATEGORY_PRIORITY["newsletter"]
    if any(k in text for k in _ACTION_KW):
        return "action", CATEGORY_PRIORITY["action"]
    return "info", CATEGORY_PRIORITY["info"]


class TriagedMail(BaseModel):
    id: str
    sender: str
    subject: str
    category: str
    priority: int
    summary: str
    draft: str | None = None  # rédaction = HERMES v2


class HermesInput(AgentInput):
    limit: int = 50


class HermesOutput(AgentOutput):
    triaged: tuple[TriagedMail, ...]
    counts: dict[str, int]
    urgent: tuple[TriagedMail, ...]


class Hermes(JarvisAgent):
    contract = AgentContract(
        name="HERMES",
        mode="scheduled",
        permissions=(Permission.MAIL_READ, Permission.MAIL_DRAFT, Permission.NET_CLOUD_INFERENCE),
        budget=Budget(max_tokens_day=50_000, max_runtime_min=2),
        inputs=HermesInput,
        outputs=HermesOutput,
    )

    # Délai max du résumé par mail ; au-delà, repli déterministe (CPU lent).
    _summary_timeout: float = 15.0

    async def run(self, data: AgentInput, ctx: AgentContext) -> AgentOutput:
        assert isinstance(data, HermesInput)
        gateway = ctx.require_gateway()
        mails = await ctx.require_mail().fetch(limit=data.limit)
        # Règles apprises (corrections utilisateur) — priment sur la classification par défaut.
        overrides = ctx.mail_memory.overrides() if ctx.mail_memory else {}
        can_draft = Permission.MAIL_DRAFT in ctx.granted
        triaged: list[TriagedMail] = []

        for mail in mails:
            await ctx.emit(
                EventType.MAIL_RECEIVED,
                id=mail.id,
                sender=mail.sender,
                subject=mail.subject,
            )
            category, priority = classify(mail, overrides)
            summary = await self._summarize(gateway, mail, ctx)
            draft = await self._maybe_draft(gateway, mail, category, ctx) if can_draft else None
            item = TriagedMail(
                id=mail.id,
                sender=mail.sender,
                subject=mail.subject,
                category=category,
                priority=priority,
                summary=summary,
                draft=draft,
            )
            triaged.append(item)
            await ctx.emit(
                EventType.MAIL_TRIAGED,
                id=mail.id,
                sender=mail.sender,
                subject=mail.subject,
                category=category,
                priority=priority,
                summary=summary,
                has_draft=draft is not None,
            )

        triaged.sort(key=lambda m: m.priority, reverse=True)
        counts = dict(Counter(m.category for m in triaged))
        urgent = tuple(m for m in triaged if m.category == "urgent")
        return HermesOutput(triaged=tuple(triaged), counts=counts, urgent=urgent)

    async def _summarize(self, gateway: InferenceGateway, mail: Mail, ctx: AgentContext) -> str:
        """Résumé une-ligne via le modèle, best-effort. Repli déterministe si lent/absent."""
        prompt = f"Résume en une phrase: {mail.subject} — {mail.body[:160]}"
        try:
            resp = await asyncio.wait_for(
                gateway.complete(
                    [ChatMessage(role="user", content=prompt)], tier="local", max_tokens=60
                ),
                timeout=self._summary_timeout,
            )
        except Exception:
            return _fallback_summary(mail)
        ctx.budget.charge(tokens=resp.usage.total_tokens)
        return resp.text.strip() or _fallback_summary(mail)

    async def _maybe_draft(
        self, gateway: InferenceGateway, mail: Mail, category: str, ctx: AgentContext
    ) -> str | None:
        """Rédige un brouillon de réponse (mails « action »/« urgent »). JAMAIS envoyé.

        Best-effort via le modèle, repli sur un gabarit déterministe. Persisté dans la
        mémoire mail (relecture UI) ; aucun canal d'envoi n'existe (`MAIL_SEND` interdite).
        """
        if category not in ("action", "urgent"):
            return None
        prompt = (
            f"Rédige un brouillon de réponse poli et bref (français) au mail suivant, "
            f"sans l'envoyer. Objet: {mail.subject}. Contenu: {mail.body[:200]}"
        )
        body = _fallback_draft(mail)
        try:
            resp = await asyncio.wait_for(
                gateway.complete(
                    [ChatMessage(role="user", content=prompt)], tier="cloud", max_tokens=180
                ),
                timeout=self._summary_timeout,
            )
            ctx.budget.charge(tokens=resp.usage.total_tokens)
            body = resp.text.strip() or body
        except Exception:
            body = _fallback_draft(mail)
        if ctx.mail_memory is not None:
            ctx.mail_memory.save_draft(mail.id, mail.sender, mail.subject, body)
        await ctx.emit(EventType.MAIL_DRAFTED, id=mail.id, sender=mail.sender, subject=mail.subject)
        return body
