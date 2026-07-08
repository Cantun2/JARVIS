"""NEMESIS — auditeur de code honnête et non complaisant.

Nom : Némésis, déesse de la juste rétribution contre l'hubris — elle ne flatte pas.
Dialogue multi-tours. Lit tes projets (lecture seule) et rend un avis qui CHALLENGE :
risques, dette, anti-patterns, classés par sévérité. Jamais « c'est bien » sans preuve.
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
from jarvis.io.files import collect_excerpts, pick_root

_SYSTEM_PROMPT = (
    "Tu es NEMESIS, auditeur de code sévère et honnête. Ton rôle est de CHALLENGER "
    "l'utilisateur, jamais de le flatter. Tu ne dis jamais « c'est bien » sans preuve. "
    "Tu identifies bugs, risques de sécurité, dette technique, anti-patterns, code mort, "
    "manques de tests, et tu les classes par sévérité (CRITIQUE / MAJEUR / MINEUR) avec, "
    "pour chacun : le fichier concerné, pourquoi c'est un problème, et une correction "
    "concrète. Si le code fourni est trop mince pour juger, dis-le franchement. Tu es direct, "
    "argumenté, sans langue de bois. Réponds en français."
)


class Nemesis(ConversationalAgent):
    contract = AgentContract(
        name="NEMESIS",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE, Permission.FS_PROJECT_DIRS),
        budget=Budget(max_tokens_day=50_000, max_runtime_min=5),
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )

    system_prompt = _SYSTEM_PROMPT
    _max_tokens = 1000

    async def _augment(
        self, messages: list[ChatMessage], data: ConversationInput, ctx: AgentContext
    ) -> list[ChatMessage]:
        try:
            root = await pick_root(ctx.require_files(), data.project)
            if root is None:
                return messages
            excerpts = await collect_excerpts(ctx.require_files(), root, max_files=12)
        except Exception:
            return messages
        if not excerpts:
            return messages
        return with_context(
            messages,
            f"Code du projet « {root} » à auditer (extraits) :\n{excerpts}\n\n"
            "Audite ce code sans complaisance.",
        )
