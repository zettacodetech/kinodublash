"""TTS provayder — MeloTTS (lokal, tez, ko'p tilli)."""
import asyncio
from pathlib import Path

from ....config import settings
from ....models import VoiceType

_model = None


def _get_model():
    global _model
    if _model is None:
        from melo.api import TTS as MeloTTS  # lazy import

        _model = MeloTTS(language=settings.MELO_TTS_LANGUAGE, device="auto")
    return _model


async def synthesize(text: str, voice: VoiceType, out_path: str | Path) -> Path:
    out_path = Path(out_path)

    def _run():
        model = _get_model()
        speaker_ids = model.hps.data.spk2id
        speaker = list(speaker_ids.values())[0]
        model.tts_to_file(text, speaker, str(out_path), speed=1.0)

    await asyncio.to_thread(_run)
    return out_path
