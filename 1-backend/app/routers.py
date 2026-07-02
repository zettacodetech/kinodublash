"""
AI "asboblar qutisi" endpointlari — dublyajdan tashqari barcha modellarni
ochiq API sifatida taqdim etadi (tarjima, chat, kod, TTS, embeddings, rasm, vision).
"""
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import settings
from .models import VoiceType
from .services import engine, registry
from .services.providers.embeddings import st_embeddings
from .services.providers.image import diffusers_image
from .services.providers.llm import groq_llm, ollama_llm
from .services.providers.vision import blip_caption, ollama_vision

router = APIRouter(prefix="/ai", tags=["AI Toolbox"])


# ---------- Sxemalar ----------
class TextIn(BaseModel):
    text: str


class PromptIn(BaseModel):
    prompt: str


class EmbedIn(BaseModel):
    texts: list[str]
    model: str | None = None


class TTSIn(BaseModel):
    text: str
    voice: VoiceType = VoiceType.MALE


# ---------- Modellar ro'yxati ----------
@router.get("/models")
async def models():
    """Tizimga ulangan barcha modellarni rol bo'yicha qaytaradi."""
    return {
        "active": {
            "stt": settings.STT_PROVIDER,
            "translation": settings.TRANSLATION_PROVIDER,
            "tts": settings.TTS_PROVIDER,
        },
        "registry": registry.list_models(),
    }


# ---------- Tarjima ----------
@router.post("/translate")
async def translate(body: TextIn):
    return {"uz": await engine.translate_to_uzbek(body.text)}


# ---------- Chat (LLM) ----------
@router.post("/chat")
async def chat(body: PromptIn):
    fn = ollama_llm.chat if settings.TRANSLATION_PROVIDER == "ollama" else groq_llm.chat
    return {"response": await fn(body.prompt)}


# ---------- Kod generatsiya (Ollama coder modellari) ----------
@router.post("/code")
async def code(body: PromptIn):
    return {"code": await ollama_llm.generate_code(body.prompt)}


# ---------- TTS (audio fayl qaytaradi) ----------
@router.post("/tts")
async def tts(body: TTSIn):
    if not body.text.strip():
        raise HTTPException(400, "Matn bo'sh.")
    out = settings.temp_dir / f"tts_{uuid.uuid4().hex}.mp3"
    await engine.synthesize(body.text, body.voice, out)
    return FileResponse(out, media_type="audio/mpeg", filename="speech.mp3")


# ---------- Embeddings ----------
@router.post("/embed")
async def embed(body: EmbedIn):
    vectors = await st_embeddings.embed(body.texts, body.model)
    return {"model": body.model or settings.EMBEDDING_MODEL, "vectors": vectors}


# ---------- Rasm generatsiya ----------
@router.post("/image")
async def image(body: PromptIn):
    out = settings.temp_dir / f"img_{uuid.uuid4().hex}.png"
    await diffusers_image.generate(body.prompt, out)
    return FileResponse(out, media_type="image/png", filename="generated.png")


# ---------- Vision: rasmni tavsiflash (Ollama LLaVA) ----------
@router.post("/vision")
async def vision(
    file: UploadFile = File(...),
    prompt: str = Form("Ushbu rasmni batafsil tasvirlab ber."),
):
    tmp = settings.temp_dir / f"vis_{uuid.uuid4().hex}.png"
    tmp.write_bytes(await file.read())
    try:
        return {"description": await ollama_vision.describe(tmp, prompt)}
    finally:
        tmp.unlink(missing_ok=True)


# ---------- Vision: BLIP caption ----------
@router.post("/caption")
async def caption(file: UploadFile = File(...)):
    tmp = settings.temp_dir / f"cap_{uuid.uuid4().hex}.png"
    tmp.write_bytes(await file.read())
    try:
        return {"caption": await blip_caption.caption(tmp)}
    finally:
        tmp.unlink(missing_ok=True)
