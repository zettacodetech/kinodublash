"""
Markaziy AI dispatcher. Dublyaj pipeline'i faqat shu modul orqali AI ni chaqiradi.
Qaysi provayder ishlashi .env dagi STT_PROVIDER / TRANSLATION_PROVIDER / TTS_PROVIDER
qiymatlariga bog'liq.

Muhim: agar birlamchi provayder ishlamasa (masalan tarmoq uzilishi — Groq
"Connection error"), avtomatik ravishda LOKAL zaxiraga o'tiladi (fallback):
  STT: groq -> faster_whisper (lokal)
  Tarjima: groq -> ollama (lokal)
Shunda tashqi tarmoq uzilsa ham dublyaj to'xtamaydi.
"""
import logging
from pathlib import Path

from ..config import settings
from ..models import VoiceType
from .speech_types import SpeechSegment

logger = logging.getLogger("dubbing.engine")


# ----------------- STT (nutq -> matn) -----------------
def _stt_provider(name: str):
    if name == "faster_whisper":
        from .providers.stt import faster_whisper_stt as p
    elif name == "openai_whisper":
        from .providers.stt import openai_whisper_stt as p
    elif name == "groq":
        from .providers.stt import groq_stt as p
    else:
        raise ValueError(f"Noma'lum STT_PROVIDER: {name}")
    return p


async def transcribe(audio_path: str | Path) -> str:
    primary = settings.STT_PROVIDER
    try:
        return await _stt_provider(primary).transcribe(audio_path)
    except Exception as exc:  # noqa: BLE001
        if primary == "groq":  # tarmoq muammosi -> lokal zaxira
            logger.warning("STT '%s' ishlamadi (%s). faster_whisper ga o'tilyapti.", primary, exc)
            return await _stt_provider("faster_whisper").transcribe(audio_path)
        raise


async def _single_segment(audio_path: str | Path, text: str) -> list[SpeechSegment]:
    text = text.strip()
    if not text:
        return []
    from . import ffmpeg_core

    duration = await ffmpeg_core.get_duration(audio_path)
    return [SpeechSegment(start=0.0, end=duration, text=text)]


async def _normalize_segment_times(audio_path: str | Path, segments: list[SpeechSegment]) -> list[SpeechSegment]:
    if not segments:
        return []
    from . import ffmpeg_core

    duration = await ffmpeg_core.get_duration(audio_path)
    if len(segments) == 1 and segments[0].end <= segments[0].start:
        return [SpeechSegment(start=0.0, end=duration, text=segments[0].text)]

    normalized: list[SpeechSegment] = []
    for seg in sorted(segments, key=lambda item: item.start):
        text = seg.text.strip()
        if not text:
            continue
        start = max(0.0, min(float(seg.start), duration))
        end = max(start, min(float(seg.end), duration))
        if end <= start:
            continue
        normalized.append(SpeechSegment(start=start, end=end, text=text))
    return normalized


async def transcribe_segments(audio_path: str | Path) -> list[SpeechSegment]:
    primary = settings.STT_PROVIDER
    try:
        provider = _stt_provider(primary)
        if hasattr(provider, "transcribe_segments"):
            segments = await provider.transcribe_segments(audio_path)
            return await _normalize_segment_times(audio_path, segments)
        return await _single_segment(audio_path, await provider.transcribe(audio_path))
    except Exception as exc:  # noqa: BLE001
        if primary == "groq":
            logger.warning("STT segmentlari '%s' ishlamadi (%s). faster_whisper ga o'tilyapti.", primary, exc)
            provider = _stt_provider("faster_whisper")
            if hasattr(provider, "transcribe_segments"):
                segments = await provider.transcribe_segments(audio_path)
                return await _normalize_segment_times(audio_path, segments)
            return await _single_segment(audio_path, await provider.transcribe(audio_path))
        raise


# ----------------- Tarjima (LLM) -----------------
def _llm_provider(name: str):
    if name == "ollama":
        from .providers.llm import ollama_llm as p
    elif name == "groq":
        from .providers.llm import groq_llm as p
    else:
        raise ValueError(f"Noma'lum TRANSLATION_PROVIDER: {name}")
    return p


async def translate_to_uzbek(text: str) -> str:
    primary = settings.TRANSLATION_PROVIDER
    try:
        return await _llm_provider(primary).translate_to_uzbek(text)
    except Exception as exc:  # noqa: BLE001
        fallback = "ollama" if primary == "groq" else "groq"
        logger.warning("Tarjima '%s' ishlamadi (%s). '%s' ga o'tilyapti.", primary, exc, fallback)
        try:
            return await _llm_provider(fallback).translate_to_uzbek(text)
        except Exception as fallback_exc:  # noqa: BLE001
            message = (
                f"Tarjima provayderlari ishlamadi: "
                f"{primary}={type(exc).__name__}; {fallback}={type(fallback_exc).__name__}"
            )
            raise RuntimeError(message) from fallback_exc


# ----------------- TTS (matn -> nutq) -----------------
def _tts_provider(name: str):
    if name == "edge":
        from .providers.tts import edge_tts_service as p
    elif name == "openai":
        from .providers.tts import openai_tts_service as p
    elif name == "coqui":
        from .providers.tts import coqui_tts_service as p
    elif name == "bark":
        from .providers.tts import bark_tts_service as p
    elif name == "chattts":
        from .providers.tts import chattts_service as p
    elif name == "melotts":
        from .providers.tts import melotts_service as p
    else:
        raise ValueError(f"Noma'lum TTS_PROVIDER: {name}")
    return p


async def synthesize(text: str, voice: VoiceType, out_path: str | Path) -> Path:
    return await _tts_provider(settings.TTS_PROVIDER).synthesize(text, voice, out_path)


async def synthesize_with_reference(
    text: str,
    voice: VoiceType,
    out_path: str | Path,
    reference_audio_path: str | Path | None = None,
) -> Path:
    provider = _tts_provider(settings.TTS_PROVIDER)
    if reference_audio_path and hasattr(provider, "synthesize_with_reference"):
        return await provider.synthesize_with_reference(text, voice, out_path, reference_audio_path)
    return await provider.synthesize(text, voice, out_path)
