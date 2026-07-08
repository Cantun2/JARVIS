"""Assemble l'InferenceGateway selon la configuration.

Ordre de résolution (cf. docs/DECISIONS.md) :
  mock (défaut)                         → MockBackend
  real + JARVIS_INFERENCE_URL présent   → OpenJarvisBackend (HTTP, aucun build Rust)
  real sans URL                         → MockBackend (repli, log d'avertissement)
"""

from __future__ import annotations

from jarvis.config import Settings
from jarvis.inference.gateway import InferenceBackend, InferenceGateway
from jarvis.inference.mock_backend import MockBackend
from jarvis.logging import get_logger

log = get_logger("jarvis.inference")


def build_backend(settings: Settings) -> InferenceBackend:
    if settings.mode == "real" and settings.ollama_url:
        from jarvis.inference.ollama_backend import OllamaBackend

        log.info("inference_backend", backend="ollama", url=settings.ollama_url)
        return OllamaBackend(settings.ollama_url, default_model=settings.local_model)
    if settings.mode == "real" and settings.inference_url:
        from jarvis.inference.openjarvis_backend import OpenJarvisBackend

        log.info("inference_backend", backend="openjarvis", url=settings.inference_url)
        return OpenJarvisBackend(
            settings.inference_url,
            api_key=settings.anthropic_api_key,
            default_model=settings.cloud_model,
        )
    if settings.mode == "real":
        log.warning("inference_backend_fallback", reason="ni JARVIS_OLLAMA_URL ni URL → mock")
    return MockBackend()


def build_gateway(settings: Settings) -> InferenceGateway:
    # Routage par tier : tâches rapides (local) sur le petit modèle, experts (cloud) sur le
    # gros modèle. Le backend Ollama sert les deux ; une clé cloud future irait vers Claude.
    tier_models = {"local": settings.local_model, "cloud": settings.expert_model}
    return InferenceGateway(build_backend(settings), tier_models=tier_models)
