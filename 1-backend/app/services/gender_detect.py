"""
Ovoz jinsini avtomatik aniqlash — audioning asosiy chastotasi (F0/pitch) orqali.
Og'ir model kerak emas: faqat numpy + stdlib `wave`. Kam RAMli mashinaga mos.

Mantiq: ovozli (voiced) freymlarda autokorrelyatsiya orqali F0 hisoblanadi,
median F0 chegaradan past bo'lsa -> erkak, aks holda -> ayol.
Erkak o'rtacha ~120 Hz, ayol ~210 Hz; chegara ~165 Hz.
"""
import asyncio
import wave
from pathlib import Path

import numpy as np

from ..models import VoiceType

_F0_MIN = 70.0
_F0_MAX = 350.0
_GENDER_THRESHOLD_HZ = 165.0


def _read_wav_mono(path: str | Path, max_seconds: float = 180.0) -> tuple[np.ndarray, int]:
    """Faqat dastlabki max_seconds ni o'qiydi — uzun (5 soatlik) fayl RAM ni to'ldirmasin."""
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        width = w.getsampwidth()
        n_frames = min(w.getnframes(), int(sr * max_seconds))
        raw = w.readframes(n_frames)
    dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(width, np.int16)
    sig = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    if nch > 1:
        sig = sig.reshape(-1, nch).mean(axis=1)
    # normalizatsiya
    peak = np.max(np.abs(sig)) or 1.0
    return sig / peak, sr


def _frame_f0(frame: np.ndarray, sr: int) -> float:
    """Bitta freym uchun autokorrelyatsiya asosida F0 (Hz). 0 = ovozsiz."""
    frame = frame - frame.mean()
    corr = np.correlate(frame, frame, mode="full")[len(frame) - 1:]
    min_lag = int(sr / _F0_MAX)
    max_lag = int(sr / _F0_MIN)
    if max_lag >= len(corr) or min_lag < 1:
        return 0.0
    segment = corr[min_lag:max_lag]
    if segment.size == 0:
        return 0.0
    peak_lag = int(np.argmax(segment)) + min_lag
    if corr[peak_lag] <= 0:
        return 0.0
    return sr / peak_lag


def _median_f0(path: str | Path) -> float:
    sig, sr = _read_wav_mono(path)
    if sig.size < sr:  # 1 soniyadan kam bo'lsa ishonchsiz
        return 0.0

    frame_len = int(0.04 * sr)   # 40 ms
    hop = int(0.02 * sr)         # 20 ms
    energy_gate = np.percentile(np.abs(sig), 60)  # jim freymlarni tashlab yuborish

    f0s: list[float] = []
    for start in range(0, len(sig) - frame_len, hop):
        frame = sig[start:start + frame_len]
        if np.mean(np.abs(frame)) < energy_gate:
            continue
        f0 = _frame_f0(frame, sr)
        if _F0_MIN < f0 < _F0_MAX:
            f0s.append(f0)
        if len(f0s) >= 800:  # yetarli namuna — tezlik uchun to'xtaymiz
            break

    if not f0s:
        return 0.0
    return float(np.median(f0s))


async def detect_voice(audio_wav_path: str | Path) -> tuple[VoiceType, float]:
    """
    Audiodagi ustun ovoz jinsini aniqlaydi.
    Qaytaradi: (VoiceType, median_f0_hz). Aniqlab bo'lmasa -> MALE (default).
    """
    median_f0 = await asyncio.to_thread(_median_f0, audio_wav_path)
    if median_f0 <= 0:
        return VoiceType.MALE, 0.0
    voice = VoiceType.MALE if median_f0 < _GENDER_THRESHOLD_HZ else VoiceType.FEMALE
    return voice, median_f0
