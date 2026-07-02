"""LLM provayder — Ollama (lokal). Tarjima, chat va kod generatsiya."""
import httpx

from ....config import settings

_TRANSLATE_SYSTEM = (
    "Sen professional dublyaj tarjimonisan. Berilgan matnni tabiiy va grammatik "
    "jihatdan to'g'ri O'ZBEK tiliga (lotin alifbosida) tarjima qil. "
    "MUHIM: iloji boricha QISQA va lo'nda yoz — tarjima asl gap bilan bir xil "
    "vaqtda aytilishi kerak, ortiqcha so'z ishlatma. Faqat tarjimani qaytar — izoh yozma."
)


async def _chat(
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
    timeout: float | None = None,
) -> str:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    async with httpx.AsyncClient(timeout=timeout or 600.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return (resp.json()["message"]["content"] or "").strip()


async def translate_to_uzbek(text: str) -> str:
    if not text.strip():
        return ""
    return await _chat(
        settings.OLLAMA_LLM_MODEL,
        _TRANSLATE_SYSTEM,
        text,
        timeout=settings.OLLAMA_TRANSLATE_TIMEOUT_SECONDS,
    )


async def chat(prompt: str, system: str = "Sen foydali yordamchisan.") -> str:
    return await _chat(settings.OLLAMA_LLM_MODEL, system, prompt, temperature=0.7)


async def generate_code(prompt: str) -> str:
    system = "Sen tajribali dasturchisan. Faqat toza, ishlaydigan kod yoz."
    return await _chat(settings.OLLAMA_CODE_MODEL, system, prompt, temperature=0.2)
