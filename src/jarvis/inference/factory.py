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
    if settings.mode == "real" and settings.inference_url:
        from jarvis.inference.openjarvis_backend import OpenJarvisBackend

        log.info("inference_backend", backend="openjarvis", url=settings.inference_url)
        return OpenJarvisBackend(
            settings.inference_url,
            api_key=settings.anthropic_api_key,
            default_model=settings.cloud_model,
        )
    if settings.mode == "real":
        log.warning("inference_backend_fallback", reason="JARVIS_INFERENCE_URL absent → mock")
    return MockBackend()


def build_gateway(settings: Settings) -> InferenceGateway:
    return InferenceGateway(build_backend(settings))
