"""TTS provayder — Coqui TTS (lokal, XTTS v2, ovoz klonlash)."""
import asyncio
from pathlib import Path

from ....config import settings
from ....models import VoiceType

_tts = None

# XTTS v2 speaker'lari (reference audio bo'lmasa fallback)
_SPEAKERS = {VoiceType.MALE: "Damien Black", VoiceType.FEMALE: "Daisy Studious"}


def _get_tts():
    global _tts
    if _tts is None:
        import os
        from TTS.api import TTS as CoquiTTS  # lazy import

        # Modelni TO'G'RIDAN-TO'G'RI lokal fayldan yuklaymiz (ModelManager qayta
        # yuklab olmasin — fayllar oldindan tayyor).
        model_dir = os.path.join(
            os.path.expanduser("~/.local/share/tts"),
            "tts_models--multilingual--multi-dataset--xtts_v2",
        )
        config_path = os.path.join(model_dir, "config.json")
        if os.path.isfile(os.path.join(model_dir, "model.pth")) and os.path.isfile(config_path):
            _tts = CoquiTTS(model_path=model_dir, config_path=config_path, progress_bar=False)
        else:
            _tts = CoquiTTS(settings.COQUI_TTS_MODEL, progress_bar=False)
    return _tts


async def synthesize_with_reference(
    text: str,
    voice: VoiceType,
    out_path: str | Path,
    reference_audio_path: str | Path | None = None,
) -> Path:
    out_path = Path(out_path)
    reference = Path(reference_audio_path) if reference_audio_path else None

    def _run():
        tts = _get_tts()
        kwargs = {
            "text": text,
            "file_path": str(out_path),
            "language": settings.COQUI_TTS_LANGUAGE,
        }
        if reference and reference.exists():
            kwargs["speaker_wav"] = str(reference)
        else:
            kwargs["speaker"] = _SPEAKERS.get(voice)
        tts.tts_to_file(**kwargs)

    await asyncio.to_thread(_run)
    return out_path


async def synthesize(text: str, voice: VoiceType, out_path: str | Path) -> Path:
    return await synthesize_with_reference(text, voice, out_path, None)
