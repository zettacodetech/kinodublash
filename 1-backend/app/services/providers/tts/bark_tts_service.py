"""TTS provayder — Suno Bark (lokal, tabiiy intonatsiya)."""
import asyncio
from pathlib import Path

from ....models import VoiceType

_loaded = False
_PRESETS = {VoiceType.MALE: "v2/en_speaker_6", VoiceType.FEMALE: "v2/en_speaker_9"}


def _ensure_loaded():
    global _loaded
    if not _loaded:
        from bark import preload_models  # lazy import

        preload_models()
        _loaded = True


async def synthesize(text: str, voice: VoiceType, out_path: str | Path) -> Path:
    out_path = Path(out_path)

    def _run():
        _ensure_loaded()
        from bark import generate_audio, SAMPLE_RATE
        from scipy.io.wavfile import write as write_wav

        audio_array = generate_audio(text, history_prompt=_PRESETS.get(voice))
        write_wav(str(out_path), SAMPLE_RATE, audio_array)

    await asyncio.to_thread(_run)
    return out_path
