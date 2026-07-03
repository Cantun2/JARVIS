"""I/O voix : oreille (STT) et voix (TTS) de JARVIS.

Même moule que `io/mail.py` / `io/telegram.py` : Protocols + backends Mock (défaut,
hors-ligne, déterministe) + adaptateurs réels derrière config + factory.

La voix est **locale uniquement** : le TTS parle sur la machine, le STT transcrit un
micro local ; aucun audio ne transite au cloud. Les adaptateurs réels (`faster-whisper`,
`piper`) sont importés paresseusement (activés via `docs/MANUAL_SETUP.md`) et acceptent
un moteur injectable → testables hors-ligne, sans jamais toucher le matériel.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from jarvis.config import Settings
from jarvis.logging import get_logger

log = get_logger("jarvis.voice")


@dataclass
class SpokenClip:
    """Trace d'une synthèse vocale. En mock, aucun son ; `path` renseigné en réel."""

    text: str
    backend: str
    path: str | None = None


@runtime_checkable
class SpeechToText(Protocol):
    async def transcribe(self, audio: bytes | None = None) -> str: ...


@runtime_checkable
class TextToSpeech(Protocol):
    async def speak(self, text: str) -> SpokenClip: ...


class MockSTT:
    """File de transcriptions injectées (déterministe, hors-ligne)."""

    def __init__(self, transcripts: tuple[str, ...] = ()) -> None:
        self._queue: deque[str] = deque(transcripts)

    def enqueue(self, *transcripts: str) -> None:
        self._queue.extend(transcripts)

    async def transcribe(self, audio: bytes | None = None) -> str:
        return self._queue.popleft() if self._queue else ""


class MockTTS:
    """Enregistre les clips en mémoire (assertions de test / affichage démo). Aucun son."""

    def __init__(self) -> None:
        self.clips: list[SpokenClip] = []

    async def speak(self, text: str) -> SpokenClip:
        clip = SpokenClip(text=text, backend="mock")
        self.clips.append(clip)
        return clip


class WhisperSTT:
    """STT réel via faster-whisper (modèle local). Moteur injectable pour les tests."""

    def __init__(self, model_path: str | None = None, *, engine: Any | None = None) -> None:
        self._model_path = model_path
        self._engine = engine

    def _build_engine(self) -> Any:
        # Import paresseux : l'extra n'est pas requis en mode mock.
        from faster_whisper import WhisperModel

        if not self._model_path:
            raise RuntimeError("JARVIS_WHISPER_MODEL_PATH manquant (cf. docs/MANUAL_SETUP.md)")
        return WhisperModel(self._model_path, device="cpu", compute_type="int8")

    async def transcribe(self, audio: bytes | None = None) -> str:
        engine = self._engine or self._build_engine()
        return await asyncio.to_thread(self._transcribe_sync, engine, audio)

    def _transcribe_sync(self, engine: Any, audio: bytes | None) -> str:
        segments, _info = engine.transcribe(audio)
        return " ".join(seg.text.strip() for seg in segments).strip()


class PiperTTS:
    """TTS réel via Piper (voix locale). Moteur injectable pour les tests."""

    def __init__(self, voice_path: str | None = None, *, engine: Any | None = None) -> None:
        self._voice_path = voice_path
        self._engine = engine

    def _build_engine(self) -> Any:
        # Import paresseux : l'extra n'est pas requis en mode mock.
        from piper.voice import PiperVoice

        if not self._voice_path:
            raise RuntimeError("JARVIS_PIPER_VOICE_PATH manquant (cf. docs/MANUAL_SETUP.md)")
        return PiperVoice.load(self._voice_path)

    async def speak(self, text: str) -> SpokenClip:
        engine = self._engine or self._build_engine()
        path = await asyncio.to_thread(self._synthesize_sync, engine, text)
        return SpokenClip(text=text, backend="piper", path=path)

    def _synthesize_sync(self, engine: Any, text: str) -> str:
        return str(engine.synthesize(text))


@dataclass
class VoiceIO:
    """Agrégat oreille + voix, avec détection du wake-word."""

    stt: SpeechToText
    tts: TextToSpeech
    wake_word: str = "jarvis"
    _spoken: list[SpokenClip] = field(default_factory=list)

    async def listen(self, audio: bytes | None = None) -> str:
        return await self.stt.transcribe(audio)

    async def speak(self, text: str) -> SpokenClip:
        clip = await self.tts.speak(text)
        self._spoken.append(clip)
        return clip

    def detect_wake(self, transcript: str) -> tuple[bool, str]:
        """(wake détecté ?, commande sans le wake-word). Tolère la ponctuation initiale."""
        stripped = transcript.strip()
        head = stripped.lower().lstrip(" ,.!:;")
        if not head.startswith(self.wake_word):
            return False, stripped
        rest = head[len(self.wake_word) :].lstrip(" ,.!:;-")
        # Retrouve la casse d'origine à partir de la longueur retirée.
        command = stripped[len(stripped) - len(rest) :] if rest else ""
        return True, command.strip()


def build_voice(settings: Settings) -> VoiceIO:
    if settings.mode == "real" and settings.voice_backend == "real":
        log.info("voice_backend", backend="whisper+piper")
        return VoiceIO(
            stt=WhisperSTT(settings.whisper_model_path),
            tts=PiperTTS(settings.piper_voice_path),
            wake_word=settings.wake_word,
        )
    return VoiceIO(stt=MockSTT(), tts=MockTTS(), wake_word=settings.wake_word)
