"""Routage du modèle par tier : experts (cloud) sur le gros modèle, tâches (local) sur le petit."""

from __future__ import annotations

from jarvis.config import Settings
from jarvis.inference.factory import build_gateway
from jarvis.inference.gateway import InferenceGateway
from jarvis.inference.mock_backend import MockBackend
from jarvis.inference.types import ChatMessage


def _msg(content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content)


async def test_tier_selects_configured_model() -> None:
    gw = InferenceGateway(
        MockBackend(), tier_models={"local": "qwen2.5:3b", "cloud": "qwen2.5:7b"}
    )
    local = await gw.complete([_msg("salut")], tier="local")
    cloud = await gw.complete([_msg("salut")], tier="cloud")
    assert local.model == "qwen2.5:3b"
    assert cloud.model == "qwen2.5:7b"


async def test_explicit_model_wins_over_tier() -> None:
    gw = InferenceGateway(MockBackend(), tier_models={"local": "qwen2.5:3b"})
    resp = await gw.complete([_msg("salut")], tier="local", model="forced-model")
    assert resp.model == "forced-model"


async def test_no_tier_models_keeps_backend_default() -> None:
    # Sans mapping (comportement historique), le backend garde son modèle par défaut.
    gw = InferenceGateway(MockBackend())
    resp = await gw.complete([_msg("salut")], tier="local")
    assert resp.model == "mock-qwen"


def test_build_gateway_wires_local_and_expert_models() -> None:
    settings = Settings(local_model="small", expert_model="big")
    gw = build_gateway(settings)
    assert gw._tier_models == {"local": "small", "cloud": "big"}
