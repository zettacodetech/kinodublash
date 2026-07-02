"""TTS provayder — ChatTTS (lokal, suhbat uslubidagi tabiiy nutq)."""
import asyncio
from pathlib import Path

from ....models import VoiceType

_chat = None


def _get_chat():
    global _chat
    if _chat is None:
        import ChatTTS  # lazy import

        _chat = ChatTTS.Chat()
        _chat.load(compile=False)
    return _chat


async def synthesize(text: str, voice: VoiceType, out_path: str | Path) -> Path:
    out_path = Path(out_path)

    def _run():
        import torch
        import torchaudio

        chat = _get_chat()
        # Har xil ovoz uchun boshqa random speaker
        seed = 1 if voice == VoiceType.MALE else 2
        torch.manual_seed(seed)
        rand_spk = chat.sample_random_speaker()
        params = chat.InferCodeParams(spk_emb=rand_spk)
        wavs = chat.infer([text], params_infer_code=params)
        torchaudio.save(str(out_path), torch.from_numpy(wavs[0]).unsqueeze(0), 24000)

    await asyncio.to_thread(_run)
    return out_path
