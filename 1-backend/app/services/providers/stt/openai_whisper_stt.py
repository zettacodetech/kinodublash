"""STT provayder — OpenAI Whisper (lokal, original implementatsiya)."""
import asyncio
from pathlib import Path

from ....config import settings
from ...speech_types import SpeechSegment

_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper  # lazy import (openai-whisper)

        _model = whisper.load_model(settings.WHISPER_MODEL_SIZE)
    return _model


async def transcribe_segments(audio_path: str | Path) -> list[SpeechSegment]:
    def _run() -> list[SpeechSegment]:
        model = _get_model()
        result = model.transcribe(str(audio_path))
        segments: list[SpeechSegment] = []
        for seg in result.get("segments") or []:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            segments.append(
                SpeechSegment(start=float(seg.get("start") or 0.0), end=float(seg.get("end") or 0.0), text=text)
            )
        if segments:
            return segments
        text = (result.get("text") or "").strip()
        return [SpeechSegment(start=0.0, end=0.0, text=text)] if text else []

    return await asyncio.to_thread(_run)


async def transcribe(audio_path: str | Path) -> str:
    segments = await transcribe_segments(audio_path)
    return " ".join(seg.text for seg in segments).strip()
