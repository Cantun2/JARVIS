"""I/O voix : mocks déterministes, wake-word, adaptateurs réels via moteur injecté."""

from __future__ import annotations

from jarvis.config import Settings
from jarvis.io.voice import (
    MockSTT,
    MockTTS,
    PiperTTS,
    VoiceIO,
    WhisperSTT,
    build_voice,
)


async def test_mock_stt_returns_queued_then_empty() -> None:
    stt = MockSTT(("bonjour", "et après"))
    assert await stt.transcribe() == "bonjour"
    assert await stt.transcribe() == "et après"
    assert await stt.transcribe() == ""  # file vide → silence


async def test_mock_tts_records_clips() -> None:
    tts = MockTTS()
    clip = await tts.speak("salut")
    assert clip.text == "salut" and clip.backend == "mock" and clip.path is None
    assert tts.clips == [clip]


async def test_voiceio_speak_and_listen() -> None:
    voice = VoiceIO(stt=MockSTT(("Jarvis, le briefing",)), tts=MockTTS())
    assert await voice.listen() == "Jarvis, le briefing"
    clip = await voice.speak("Bonjour.")
    assert clip.text == "Bonjour."


def test_detect_wake_present_and_absent() -> None:
    voice = VoiceIO(stt=MockSTT(), tts=MockTTS(), wake_word="jarvis")
    wake, command = voice.detect_wake("Jarvis, fais le point")
    assert wake is True and command == "fais le point"
    wake2, command2 = voice.detect_wake("quelle heure est-il ?")
    assert wake2 is False and command2 == "quelle heure est-il ?"


def test_detect_wake_is_case_and_punctuation_tolerant() -> None:
    voice = VoiceIO(stt=MockSTT(), tts=MockTTS(), wake_word="jarvis")
    wake, command = voice.detect_wake("  JARVIS : Résume ma journée")
    assert wake is True and command == "Résume ma journée"


def test_build_voice_mock_by_default() -> None:
    voice = build_voice(Settings(mode="mock"))
    assert isinstance(voice.stt, MockSTT)
    assert isinstance(voice.tts, MockTTS)
    assert voice.wake_word == "jarvis"


class _FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeWhisper:
    def transcribe(self, audio: object) -> tuple[list[_FakeSegment], object]:
        return [_FakeSegment(" bonjour "), _FakeSegment("monde")], object()


async def test_whisper_adapter_uses_injected_engine() -> None:
    stt = WhisperSTT(engine=_FakeWhisper())
    assert await stt.transcribe(b"...") == "bonjour monde"


class _FakePiper:
    def synthesize(self, text: str) -> str:
        return f"/tmp/{len(text)}.wav"


async def test_piper_adapter_uses_injected_engine() -> None:
    tts = PiperTTS(engine=_FakePiper())
    clip = await tts.speak("salut")
    assert clip.backend == "piper" and clip.path == "/tmp/5.wav"
