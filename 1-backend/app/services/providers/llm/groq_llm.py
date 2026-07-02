"""LLM provayder — Groq (bulut, Llama 3.3)."""
import logging
import time

from groq import AsyncGroq

from ....config import settings

logger = logging.getLogger("dubbing.groq_llm")

# Rate-limit bo'lsa SDK 1 daqiqagacha kutib retry qilmasin; key rotation/fallback darhol ishlasin.
_clients = [AsyncGroq(api_key=key, max_retries=0, timeout=90.0) for key in settings.groq_api_keys]
_disabled_until: dict[int, float] = {}

_TRANSLATE_SYSTEM = (
    "Sen professional dublyaj tarjimonisan. Berilgan matnni tabiiy va grammatik "
    "jihatdan to'g'ri O'ZBEK tiliga (lotin alifbosida) tarjima qil. "
    "MUHIM: iloji boricha QISQA va lo'nda yoz — tarjima asl gap bilan bir xil "
    "vaqtda aytilishi kerak, shuning uchun ortiqcha so'z ishlatma, ma'noni "
    "qisqa yetkaz. Faqat tarjimani qaytar — hech qanday izoh yozma."
)


def _completion_limit(text: str) -> int:
    """Small segments should not burn thousands of Groq daily tokens."""
    return max(256, min(2048, (len(text) // 2) + 256))


async def _chat(system: str, user: str, temperature: float = 0.3, max_tokens: int | None = None) -> str:
    if not _clients:
        raise RuntimeError("GROQ_API_KEYS/GROQ_API_KEY sozlanmagan.")

    limit = max_tokens or _completion_limit(user)
    last_error: Exception | None = None
    now = time.monotonic()
    for index, client in enumerate(_clients, start=1):
        if _disabled_until.get(index, 0.0) > now:
            continue
        try:
            completion = await client.chat.completions.create(
                model=settings.GROQ_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=limit,
            )
            return (completion.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            status_code = getattr(exc, "status_code", None)
            if status_code == 401:
                _disabled_until[index] = time.monotonic() + 3600
            elif status_code == 429:
                _disabled_until[index] = time.monotonic() + 60
            if index < len(_clients):
                logger.warning("Groq LLM %d-key ishlamadi (%s). Keyingi key sinab ko'rilyapti.", index, exc)
                continue
            raise

    raise RuntimeError("Groq LLM keylari vaqtincha ishlamayapti.") from last_error


async def translate_to_uzbek(text: str) -> str:
    if not text.strip():
        return ""
    return await _chat(_TRANSLATE_SYSTEM, text)


async def chat(prompt: str, system: str = "Sen foydali yordamchisan.") -> str:
    return await _chat(system, prompt, temperature=0.7)
