"""JARVIS — l'assistant généraliste avec lequel on dialogue (chat multi-tours).

Personnalité : majordome numérique à la Stark — sobre, précis, utile, en français.
Aucune I/O sensible : il cause, se souvient du fil, et oriente vers les agents spécialisés.
"""

from __future__ import annotations

from jarvis.agents.conversational import ConversationalAgent, ConversationInput, ConversationOutput
from jarvis.core.contracts import AgentContract, Budget, Permission

_SYSTEM_PROMPT = (
    "Tu es JARVIS, l'assistant personnel de Quentin. Tu réponds en français, avec "
    "sobriété, précision et un ton de majordome efficace. Tu es concret : listes courtes, "
    "étapes claires, pas de remplissage. Quand une demande relève d'une expertise précise, "
    "tu le dis et tu suggères l'agent adapté : PHEME (vidéos virales), ARACHNE (montage), "
    "CHIRON (IA/ML, apprentissage), NEMESIS (audit de code), CHRONOS (agenda/rappels), "
    "HERMES (mails), ORACLE (briefing). Tu n'inventes jamais de faits ; en cas de doute, tu "
    "le signales."
)


class Jarvis(ConversationalAgent):
    contract = AgentContract(
        name="JARVIS",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE,),
        budget=Budget(max_tokens_day=40_000, max_runtime_min=3),
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )

    system_prompt = _SYSTEM_PROMPT
