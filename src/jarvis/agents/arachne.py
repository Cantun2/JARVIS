"""ARACHNE — spécialiste du montage vidéo.

Nom : Arachne, la tisseuse — le montage tisse plans, rythme et récit en un tout.
Dialogue multi-tours, sans I/O sensible : conseil pur (rythme, hooks, coupe, outils).
"""

from __future__ import annotations

from jarvis.agents.conversational import ConversationalAgent, ConversationInput, ConversationOutput
from jarvis.core.contracts import AgentContract, Budget, Permission

_SYSTEM_PROMPT = (
    "Tu es ARACHNE, spécialiste du montage vidéo orienté rétention. Tu maîtrises le rythme "
    "de coupe, la structure de hook, les b-rolls, le sound design, les sous-titres dynamiques "
    "et les outils (DaVinci Resolve, Premiere Pro, CapCut, Final Cut). Tu donnes des recettes "
    "concrètes : où couper, quand accélérer, comment garder l'attention, quels réglages export "
    "par plateforme. Réponds en français, précis, avec des étapes reproductibles."
)


class Arachne(ConversationalAgent):
    contract = AgentContract(
        name="ARACHNE",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE,),
        budget=Budget(max_tokens_day=40_000, max_runtime_min=3),
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )

    system_prompt = _SYSTEM_PROMPT
    _max_tokens = 800
