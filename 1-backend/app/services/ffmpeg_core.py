"""
FFmpeg yadrosi — asinxron subprocess orqali:
  1) videodan audio ajratish,
  2) media davomiyligini o'lchash (ffprobe),
  3) o'zbekcha audioni original video vaqtiga aniq moslashtirish (atempo time-stretch),
  4) yangi audioni videoga yopishtirish.
"""
import asyncio
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


async def _run(*args: str) -> str:
    """FFmpeg/ffprobe buyrug'ini asinxron ishga tushiradi."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise FFmpegError(
            f"'{args[0]}' xatolik bilan tugadi (code={proc.returncode}):\n"
            f"{stderr.decode(errors='ignore')[-2000:]}"
        )
    return stdout.decode(errors="ignore")


async def get_duration(media_path: str | Path) -> float:
    """Media faylning davomiyligini soniyalarda qaytaradi (ffprobe)."""
    out = await _run(
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    )
    try:
        return float(out.strip())
    except ValueError as exc:
        raise FFmpegError(f"Davomiylikni o'qib bo'lmadi: {out!r}") from exc


async def extract_audio(video_path: str | Path, out_wav: str | Path) -> Path:
    """Videodan audioni WAV (16kHz mono) sifatida ajratadi — Whisper uchun ideal."""
    out_wav = Path(out_wav)
    await _run(
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",                      # video yo'q
        "-ac", "1",                 # mono
        "-ar", "16000",             # 16 kHz
        "-c:a", "pcm_s16le",
        str(out_wav),
    )
    return out_wav


async def extract_audio_clip(
    audio_path: str | Path,
    start: float,
    duration: float,
    out_wav: str | Path,
    sr: int = 16000,
) -> Path:
    """Audio ichidan qisqa reference bo'lak kesib oladi (voice clone/gender uchun)."""
    out_wav = Path(out_wav)
    await _run(
        "ffmpeg", "-y",
        "-ss", f"{max(start, 0.0):.3f}",
        "-t", f"{max(duration, 0.1):.3f}",
        "-i", str(audio_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sr),
        "-c:a", "pcm_s16le",
        str(out_wav),
    )
    return out_wav


def _build_atempo_chain(factor: float) -> str:
    """
    atempo filtri faqat 0.5–2.0 oralig'ida ishlaydi. Kerak bo'lsa bir nechta
    atempo filtrini ketma-ket ulab, istalgan koeffitsientga erishamiz.
    factor > 1  -> tezlashtirish (audio uzunroq bo'lsa)
    factor < 1  -> sekinlashtirish (audio qisqaroq bo'lsa)
    """
    factor = max(0.25, min(factor, 4.0))  # xavfsiz chegara
    filters: list[str] = []
    remaining = factor
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters)


async def fit_audio_to_duration(
    audio_path: str | Path,
    target_duration: float,
    out_path: str | Path,
    max_speedup: float = 2.0,
    min_slowdown: float = 0.9,
) -> Path:
    """
    Har segment ovozini AVTOMATIK ravishda original gap davomiyligiga
    (odam o'sha gapni qancha vaqtda aytgan bo'lsa) moslaydi:
      - TTS uzunroq bo'lsa  -> kerakligicha tezlashtiradi (max_speedup gacha),
        odatda aynan gap vaqtiga sig'adi (sinxron). Faqat juda uzun bo'lsa cheklaydi.
      - TTS qisqaroq bo'lsa -> biroz sekinlashtiradi (min_slowdown gacha), so'ng
        qolgan bo'sh vaqtni jimlik bilan to'ldiradi (odam gapirayotganda dub o'chib
        qolmasin). Shunday qilib tezlik odam gapirish tempiga qarab o'zi tanlanadi.
    """
    out_path = Path(out_path)
    audio_dur = await get_duration(audio_path)
    if audio_dur <= 0 or target_duration <= 0:
        raise FFmpegError("Noto'g'ri davomiylik qiymatlari.")

    factor = audio_dur / target_duration

    if factor >= 1.0:
        # Uzun -> odam tempiga moslab tezlashtiramiz (max_speedup gacha)
        speed = min(factor, max(1.0, max_speedup))
        atempo = _build_atempo_chain(speed)
        await _run(
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-filter:a", atempo,
            "-ar", "24000", "-ac", "1",
            str(out_path),
        )
    else:
        # Qisqa -> biroz sekinlashtiramiz (min_slowdown dan pastga tushmaymiz), keyin jimlik
        speed = max(factor, min(1.0, min_slowdown))
        atempo = _build_atempo_chain(speed)
        await _run(
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-filter:a", f"{atempo},apad",
            "-t", f"{target_duration:.3f}",
            "-ar", "24000", "-ac", "1",
            str(out_path),
        )
    return out_path


async def split_audio(
    audio_path: str | Path, segment_seconds: int, out_dir: str | Path
) -> list[Path]:
    """Audioni segment_seconds uzunlikdagi bo'laklarga bo'ladi (uzun videolar uchun)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "chunk_%04d.wav")
    await _run(
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-f", "segment",
        "-segment_time", str(segment_seconds),
        "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
        pattern,
    )
    return sorted(out_dir.glob("chunk_*.wav"))


async def make_silence(duration: float, out_path: str | Path, sr: int = 24000) -> Path:
    """Berilgan davomiylikdagi jimlik (silence) audio yaratadi (nutqsiz bo'laklar uchun)."""
    out_path = Path(out_path)
    await _run(
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
        "-t", f"{max(duration, 0.1):.3f}",
        "-c:a", "pcm_s16le",
        str(out_path),
    )
    return out_path


async def set_exact_duration(audio_path: str | Path, duration: float, out_path: str | Path) -> Path:
    """Audioni ANIQ `duration` ga tenglaydi: qisqa bo'lsa jimlik qo'shadi, uzun bo'lsa kesadi.
    Bo'laklar chegarasi video bilan sinxron qolishi uchun ishlatiladi."""
    out_path = Path(out_path)
    await _run(
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-af", "apad",
        "-t", f"{max(duration, 0.05):.3f}",
        "-ar", "24000", "-ac", "1",
        str(out_path),
    )
    return out_path


async def concat_audio(paths: list[str | Path], out_path: str | Path) -> Path:
    """Bir nechta audio bo'lakni ketma-ket bitta faylga birlashtiradi."""
    out_path = Path(out_path)
    list_file = out_path.with_suffix(".concat.txt")
    list_file.write_text(
        "".join(f"file '{Path(p).resolve()}'\n" for p in paths), encoding="utf-8"
    )
    try:
        await _run(
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1",
            str(out_path),
        )
    finally:
        list_file.unlink(missing_ok=True)
    return out_path


async def mux_audio_into_video(
    video_path: str | Path,
    audio_path: str | Path,
    out_path: str | Path,
) -> Path:
    """
    Yangi (o'zbekcha) audioni videoga yopishtiradi. Video oqimi qayta
    kodlanmaydi (-c:v copy), audio esa AAC ga o'giriladi. Eng qisqa oqim
    bo'yicha kesiladi (-shortest).
    """
    out_path = Path(out_path)
    await _run(
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_path),
    )
    return out_path
