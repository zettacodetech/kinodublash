"""TTS provayder — Edge-TTS (BEPUL, native o'zbek ovozlari).

Voice cloning (Coqui XTTS) og'ir GPU talab qiladi. Bu yerda LOKAL, CPU-da ishlaydigan
yengil alternativa: reference audiodagi ovoz balandligini (F0) o'lchab, edge-tts
ovozini o'sha registrga moslaymiz (pitch matching). To'liq klon emas, lekin ovozni
asl odamnikiga ancha yaqinlashtiradi.
"""
from pathlib import Path

from ....config import settings
from ....models import VoiceType
from ... import gender_detect

# Edge o'zbek ovozlarining taxminiy asosiy chastotasi (Hz)
_BASE_F0 = {VoiceType.MALE: 130.0, VoiceType.FEMALE: 210.0}
_MAX_PITCH_SHIFT = 60  # Hz — haddan tashqari buzilmasin


def _voice_for(voice: VoiceType) -> str:
    return (
        settings.EDGE_TTS_VOICE_MALE
        if voice == VoiceType.MALE
        else settings.EDGE_TTS_VOICE_FEMALE
    )


async def _pitch_offset(voice: VoiceType, reference_audio_path) -> int:
    """Reference ovoz F0 sini o'lchab, edge ovozga nisbatan pitch siljishini (Hz) qaytaradi."""
    try:
        _detected, f0 = await gender_detect.detect_voice(reference_audio_path)
        if f0 and f0 > 0:
            base = _BASE_F0.get(voice, 130.0)
            return int(max(-_MAX_PITCH_SHIFT, min(_MAX_PITCH_SHIFT, f0 - base)))
    except Exception:  # noqa: BLE001 — pitch moslash ixtiyoriy
        pass
    return 0


async def _speak(text: str, voice: VoiceType, out_path: Path, pitch_hz: int = 0) -> Path:
    import edge_tts  # lazy import

    kwargs = {}
    if pitch_hz:
        kwargs["pitch"] = f"{pitch_hz:+d}Hz"
    communicate = edge_tts.Communicate(text, _voice_for(voice), **kwargs)
    await communicate.save(str(out_path))
    return out_path


async def synthesize(text: str, voice: VoiceType, out_path: str | Path) -> Path:
    return await _speak(text, voice, Path(out_path), 0)


async def synthesize_with_reference(
    text: str,
    voice: VoiceType,
    out_path: str | Path,
    reference_audio_path: str | Path | None = None,
) -> Path:
    """Reference ovozga qarab pitch'ni moslab so'zlaydi (lokal 'voice matching')."""
    pitch = await _pitch_offset(voice, reference_audio_path) if reference_audio_path else 0
    return await _speak(text, voice, Path(out_path), pitch)
