"""STT provayder — faster-whisper (lokal, tez, CPU/GPU)."""
import asyncio
from pathlib import Path

from ....config import settings
from ...speech_types import SpeechSegment

_model = None


def _get_model():
    """Modelni bir marta yuklab, keshda saqlaydi (og'ir operatsiya)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # lazy import

        device = settings.WHISPER_DEVICE
        if device == "auto":
            try:
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        _model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device=device,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
    return _model


async def transcribe_segments(audio_path: str | Path) -> list[SpeechSegment]:
    def _run() -> list[SpeechSegment]:
        model = _get_model()
        segments, _info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
        result: list[SpeechSegment] = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            result.append(SpeechSegment(start=float(seg.start), end=float(seg.end), text=text))
        return result

    # Blocking operatsiyani alohida threadda ishga tushiramiz (event loopni bloklamaslik uchun)
    return await asyncio.to_thread(_run)


async def transcribe(audio_path: str | Path) -> str:
    segments = await transcribe_segments(audio_path)
    return " ".join(seg.text for seg in segments).strip()
