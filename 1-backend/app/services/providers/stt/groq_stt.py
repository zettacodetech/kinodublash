"""STT provayder — Groq Whisper (bulut)."""
import logging
import time
from pathlib import Path

from groq import AsyncGroq

from ....config import settings
from ...speech_types import SpeechSegment

logger = logging.getLogger("dubbing.groq_stt")

# Rate-limit bo'lsa SDK uzoq kutmasin; key rotation/fallback darhol ishlasin.
_clients = [AsyncGroq(api_key=key, max_retries=0, timeout=90.0) for key in settings.groq_api_keys]
_disabled_until: dict[int, float] = {}


async def transcribe(audio_path: str | Path) -> str:
    if not _clients:
        raise RuntimeError("GROQ_API_KEYS/GROQ_API_KEY sozlanmagan.")
    audio_path = Path(audio_path)
    last_error: Exception | None = None
    now = time.monotonic()
    for index, client in enumerate(_clients, start=1):
        if _disabled_until.get(index, 0.0) > now:
            continue
        try:
            with audio_path.open("rb") as f:
                result = await client.audio.transcriptions.create(
                    file=(audio_path.name, f.read()),
                    model=settings.GROQ_WHISPER_MODEL,
                    response_format="text",
                    temperature=0.0,
                )
            return (result if isinstance(result, str) else getattr(result, "text", "")).strip()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            status_code = getattr(exc, "status_code", None)
            if status_code == 401:
                _disabled_until[index] = time.monotonic() + 3600
            elif status_code == 429:
                _disabled_until[index] = time.monotonic() + 60
            if index < len(_clients):
                logger.warning("Groq STT %d-key ishlamadi (%s). Keyingi key sinab ko'rilyapti.", index, exc)
                continue
            raise

    raise RuntimeError("Groq STT keylari vaqtincha ishlamayapti.") from last_error


def _get_field(obj, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


async def transcribe_segments(audio_path: str | Path) -> list[SpeechSegment]:
    if not _clients:
        raise RuntimeError("GROQ_API_KEYS/GROQ_API_KEY sozlanmagan.")
    audio_path = Path(audio_path)
    last_error: Exception | None = None
    now = time.monotonic()
    for index, client in enumerate(_clients, start=1):
        if _disabled_until.get(index, 0.0) > now:
            continue
        try:
            with audio_path.open("rb") as f:
                result = await client.audio.transcriptions.create(
                    file=(audio_path.name, f.read()),
                    model=settings.GROQ_WHISPER_MODEL,
                    response_format="verbose_json",
                    temperature=0.0,
                )
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            status_code = getattr(exc, "status_code", None)
            if status_code == 401:
                _disabled_until[index] = time.monotonic() + 3600
            elif status_code == 429:
                _disabled_until[index] = time.monotonic() + 60
            if index < len(_clients):
                logger.warning("Groq STT segment %d-key ishlamadi (%s). Keyingi key sinab ko'rilyapti.", index, exc)
                continue
            raise
    else:
        raise RuntimeError("Groq STT segment keylari vaqtincha ishlamayapti.") from last_error

    segments: list[SpeechSegment] = []
    for seg in _get_field(result, "segments", []) or []:
        text = (_get_field(seg, "text", "") or "").strip()
        if not text:
            continue
        segments.append(
            SpeechSegment(
                start=float(_get_field(seg, "start", 0.0) or 0.0),
                end=float(_get_field(seg, "end", 0.0) or 0.0),
                text=text,
            )
        )
    if segments:
        return segments

    text = (_get_field(result, "text", "") or "").strip()
    return [SpeechSegment(start=0.0, end=0.0, text=text)] if text else []
