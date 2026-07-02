"""Vision provayder — Ollama (LLaVA, moondream, qwen2-vl, MiniCPM-V)."""
import base64
from pathlib import Path

import httpx

from ....config import settings


async def describe(image_path: str | Path, prompt: str = "Ushbu rasmni batafsil tasvirlab ber.") -> str:
    image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_VISION_MODEL,
        "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return (resp.json()["message"]["content"] or "").strip()
