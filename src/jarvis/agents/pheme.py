"""PHEME — experte en vidéos virales (toutes plateformes).

Nom : Pheme, déesse grecque de la rumeur et de la propagation — l'incarnation du « viral ».
Dialogue multi-tours. Recherche le web (mock par défaut) pour ancrer ses conseils sur ce qui
performe réellement, puis répond avec des angles concrets par plateforme.
"""

from __future__ import annotations

from jarvis.agents.conversational import (
    ConversationalAgent,
    ConversationInput,
    ConversationOutput,
    with_context,
)
from jarvis.core.context import AgentContext
from jarvis.core.contracts import AgentContract, Budget, Permission
from jarvis.inference.types import ChatMessage

_SYSTEM_PROMPT = (
    "Tu es PHEME, experte des vidéos virales sur TikTok, YouTube (Shorts et long), "
    "Instagram Reels et Facebook. Tu penses en termes de HOOK (3 premières secondes), "
    "rétention, format, tendance, et boucle de partage. Tu donnes des conseils concrets et "
    "actionnables, adaptés à la plateforme, avec des exemples d'accroches et de structures. "
    "Domaine de prédilection de l'utilisateur : sport d'endurance et défis un peu fous — "
    "exploite-le. Réponds en français, sans blabla, avec des listes courtes."
)


class Pheme(ConversationalAgent):
    contract = AgentContract(
        name="PHEME",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE, Permission.NET_WEB),
        budget=Budget(max_tokens_day=40_000, max_runtime_min=3),
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )

    system_prompt = _SYSTEM_PROMPT
    _max_tokens = 800

    async def _augment(
        self, messages: list[ChatMessage], data: ConversationInput, ctx: AgentContext
    ) -> list[ChatMessage]:
        try:
            results = await ctx.require_web().search(data.message, limit=5)
        except Exception:
            return messages
        if not results:
            return messages
        lines = "\n".join(f"- {r.title} — {r.url}\n  {r.snippet}" for r in results)
        return with_context(
            messages,
            "Résultats de recherche web récents (à exploiter, avec esprit critique) :\n" + lines,
        )
