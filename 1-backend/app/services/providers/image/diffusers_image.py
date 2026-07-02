"""
Rasm generatsiya provayderi — diffusers.
Modellar: SDXL, SDXL-Turbo, FLUX.1, LCM-SDXL, PixArt, openjourney.
"""
import asyncio
from pathlib import Path

from ....config import settings

_pipe = None


def _get_pipe():
    global _pipe
    if _pipe is None:
        import torch
        from diffusers import AutoPipelineForText2Image  # lazy import

        dtype = torch.float16 if settings.IMAGE_DEVICE == "cuda" else torch.float32
        _pipe = AutoPipelineForText2Image.from_pretrained(
            settings.IMAGE_MODEL, torch_dtype=dtype
        ).to(settings.IMAGE_DEVICE)
    return _pipe


async def generate(prompt: str, out_path: str | Path, steps: int = 4) -> Path:
    out_path = Path(out_path)

    def _run():
        pipe = _get_pipe()
        # SDXL-Turbo/LCM uchun kam qadam (steps), guidance=0.0 tavsiya etiladi
        image = pipe(prompt=prompt, num_inference_steps=steps, guidance_scale=0.0).images[0]
        image.save(str(out_path))

    await asyncio.to_thread(_run)
    return out_path
