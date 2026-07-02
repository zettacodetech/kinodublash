"""Vision provayder — BLIP (lokal, rasmga izoh/caption)."""
import asyncio
from pathlib import Path

from ....config import settings

_processor = None
_model = None


def _load():
    global _processor, _model
    if _model is None:
        from transformers import BlipForConditionalGeneration, BlipProcessor  # lazy import

        _processor = BlipProcessor.from_pretrained(settings.BLIP_MODEL)
        _model = BlipForConditionalGeneration.from_pretrained(settings.BLIP_MODEL)
    return _processor, _model


async def caption(image_path: str | Path) -> str:
    def _run():
        from PIL import Image

        processor, model = _load()
        image = Image.open(str(image_path)).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=60)
        return processor.decode(out[0], skip_special_tokens=True).strip()

    return await asyncio.to_thread(_run)
