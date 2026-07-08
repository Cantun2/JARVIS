"""CHIRON — tuteur IA/ML (t'apprend ET t'aide sur tes projets).

Nom : Chiron, le centaure précepteur des héros — l'archétype du mentor.
Dialogue multi-tours. Peut lire un projet (lecture seule) pour ancrer son aide sur ton code.
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
    "Tu es CHIRON, tuteur en IA et machine learning. Tu enseignes avec clarté (intuition "
    "d'abord, puis formalisme, puis code) ET tu aides concrètement sur les projets de "
    "l'utilisateur. Tu adaptes la profondeur au niveau de la question, tu cites les concepts "
    "clés, tu proposes des exercices et des pistes de lecture. Quand du code de projet est "
    "fourni en contexte, tu t'appuies dessus. Réponds en français, pédagogique mais concis."
)


class Chiron(ConversationalAgent):
    contract = AgentContract(
        name="CHIRON",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE, Permission.FS_PROJECT_DIRS),
        budget=Budget(max_tokens_day=40_000, max_runtime_min=4),
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )

    system_prompt = _SYSTEM_PROMPT
    _max_tokens = 900

    async def _augment(
        self, messages: list[ChatMessage], data: ConversationInput, ctx: AgentContext
    ) -> list[ChatMessage]:
        # N'ancre sur le code que si l'utilisateur a nommé un projet.
        if not data.project:
            return messages
        try:
            root = await pick_root(ctx.require_files(), data.project)
            if root is None:
                return messages
            excerpts = await collect_excerpts(ctx.require_files(), root, max_files=8)
        except Exception:
            return messages
        if not excerpts:
            return messages
        return with_context(messages, f"Extraits du projet « {root} » :\n{excerpts}")
