"""
YouTube (va boshqa saytlar) dan videoni yt-dlp orqali eng yaxshi sifatda yuklab oladi.
FFmpeg mavjud bo'lgani uchun video+audio oqimlari mp4 ga birlashtiriladi.
"""
import asyncio
import os
import re
from pathlib import Path

from ..config import settings

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_YT_RE = re.compile(r"(youtube\.com|youtu\.be)", re.IGNORECASE)


def find_url(text: str) -> str | None:
    m = _URL_RE.search(text or "")
    return m.group(0) if m else None


def is_youtube(url: str) -> bool:
    return bool(_YT_RE.search(url or ""))


class YoutubeError(RuntimeError):
    pass


async def get_duration(url: str) -> float | None:
    """Havoladagi video davomiyligini (soniya) metadata orqali tez oladi (yuklamasdan)."""
    cmd = ["yt-dlp", "--no-warnings", "--skip-download", "--print", "duration",
           "--extractor-args", f"youtube:player_client={settings.YT_DLP_PLAYER_CLIENT}"]
    if settings.YT_DLP_COOKIES and os.path.isfile(settings.YT_DLP_COOKIES):
        cmd += ["--cookies", settings.YT_DLP_COOKIES]
    cmd.append(url)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _err = await proc.communicate()
        return float(out.decode(errors="ignore").strip().splitlines()[0])
    except Exception:  # noqa: BLE001 — ETA ixtiyoriy, xato bo'lsa None
        return None


async def download(url: str, out_path: str | Path, max_height: int = 1080) -> Path:
    """
    Videoni yuklab oladi. `out_path` — yakuniy .mp4 fayl.
    max_height — sifat cheklovi (masalan 1080p); serverni haddan tashqari
    yuklamaslik uchun. Original sifat kerak bo'lsa kattaroq qiling.
    """
    out_path = Path(out_path)
    fmt = f"bv*[height<={max_height}]+ba/b[height<={max_height}]/bv*+ba/b"
    cmd = [
        "yt-dlp",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-warnings",
        "--force-overwrites",
        # YouTube throttling (429) va bot-tekshiruvini yumshatish
        "--extractor-args", f"youtube:player_client={settings.YT_DLP_PLAYER_CLIENT}",
        "--retries", "10",
        "--fragment-retries", "10",
        "--retry-sleep", "5",
    ]
    # YouTube ko'pincha "Sign in to confirm you're not a bot" so'raydi -> cookies kerak
    if settings.YT_DLP_COOKIES and os.path.isfile(settings.YT_DLP_COOKIES):
        cmd += ["--cookies", settings.YT_DLP_COOKIES]
    cmd += ["-o", str(out_path), url]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _out, err = await proc.communicate()
    if proc.returncode != 0:
        raise YoutubeError(
            f"yt-dlp xatolik (code={proc.returncode}): {err.decode(errors='ignore')[-1500:]}"
        )
    if not out_path.exists():
        # yt-dlp ba'zan kengaytmani o'zgartiradi — mos faylni topamiz
        candidates = list(out_path.parent.glob(f"{out_path.stem}.*"))
        if candidates:
            return candidates[0]
        raise YoutubeError("Yuklab olingan fayl topilmadi.")
    return out_path
