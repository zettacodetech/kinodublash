"""TTS provayder — OpenAI TTS (bulut, onyx/nova)."""
from pathlib import Path

from openai import AsyncOpenAI

from ....config import settings
from ....models import VoiceType

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
_MAX_CHARS = 3800


def _voice_for(voice: VoiceType) -> str:
    return settings.TTS_VOICE_MALE if voice == VoiceType.MALE else settings.TTS_VOICE_FEMALE


def _chunk_text(text: str, limit: int = _MAX_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    chunks, current = [], ""
    for sentence in text.replace("\n", " ").split(". "):
        piece = sentence if sentence.endswith(".") else sentence + ". "
        if len(current) + len(piece) > limit:
            if current:
                chunks.append(current.strip())
            current = piece
        else:
            current += piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


async def _stream_to_file(text: str, voice_name: str, path: Path) -> None:
    async with _client.audio.speech.with_streaming_response.create(
        model=settings.OPENAI_TTS_MODEL,
        voice=voice_name,
        input=text,
        response_format="mp3",
    ) as response:
        await response.stream_to_file(path)


async def synthesize(text: str, voice: VoiceType, out_path: str | Path) -> Path:
    if _client is None:
        raise RuntimeError("OPENAI_API_KEY sozlanmagan.")
    out_path = Path(out_path)
    voice_name = _voice_for(voice)
    chunks = _chunk_text(text)
    if not chunks:
        raise ValueError("TTS uchun matn bo'sh.")

    if len(chunks) == 1:
        await _stream_to_file(chunks[0], voice_name, out_path)
        return out_path

    parts = []
    for i, chunk in enumerate(chunks):
        part = out_path.with_name(f"{out_path.stem}_part{i}.mp3")
        await _stream_to_file(chunk, voice_name, part)
        parts.append(part)
    with out_path.open("wb") as dst:
        for part in parts:
            dst.write(part.read_bytes())
            part.unlink(missing_ok=True)
    return out_path
