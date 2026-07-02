"""
Bot handlerlari:
  1) video qabul qilinsa -> ovoz turi AVTOMATIK aniqlanadi (savol yo'q),
  2) YouTube (yoki boshqa) havola yuborilsa -> backend o'zi yuklab oladi,
  3) har 5 soniyada status tekshiriladi,
  4) tayyor video foydalanuvchiga qaytariladi.
Katta fayllar (2GB gacha) disk<->tarmoq oqim orqali uzatiladi (RAM tejaladi).
"""
import asyncio
import logging
import os
import tempfile
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from .api_client import BackendClient
from .config import settings

router = Router()
logger = logging.getLogger("dubbing.bot")

backend = BackendClient()
TMP_DIR = Path(tempfile.gettempdir())

STAGE_LABELS = {
    "queued": "⏳ Navbatda...",
    "download": "⬇️ Havoladan yuklab olinmoqda...",
    "audio_extract": "🎧 Audio ajratilmoqda...",
    "voice_detect": "🕵️ Ovoz turi aniqlanmoqda...",
    "transcribe": "📝 Nutq matnga o'girilmoqda...",
    "translate": "🌐 O'zbekchaga tarjima qilinmoqda...",
    "tts": "🔊 Ovoz generatsiya qilinmoqda...",
    "time_stretch": "⏱ Vaqt moslashtirilmoqda...",
    "mux": "🎬 Video yig'ilmoqda...",
    "completed": "✅ Tayyor!",
    "failed": "❌ Xatolik",
}


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Salom! Men videolarni chet tilidan <b>o'zbek tiliga</b> tarjima qilib, "
        "ovozlashtiruvchi (dublyaj) botman.\n\n"
        "📹 Menga <b>video</b> yuboring — ovoz turini (erkak/ayol) o'zim aniqlayman.\n"
        "🔗 Yoki <b>YouTube havolasini</b> yuboring — kino/serialni o'zbekchaga o'girib beraman."
    )


@router.message(F.video | F.document)
async def on_video(message: Message) -> None:
    """Video kelganda ovoz AVTOMATIK aniqlanadi va dublyaj boshlanadi."""
    file_id, file_size = None, 0
    if message.video:
        file_id, file_size = message.video.file_id, message.video.file_size or 0
    elif message.document and (message.document.mime_type or "").startswith("video/"):
        file_id, file_size = message.document.file_id, message.document.file_size or 0

    if not file_id:
        await message.answer("❌ Iltimos, video fayl yuboring.")
        return

    if file_size > settings.MAX_VIDEO_MB * 1024 * 1024:
        await message.answer(
            f"⚠️ Video juda katta ({file_size // (1024*1024)}MB). "
            f"Bot orqali maksimum {settings.MAX_VIDEO_MB}MB. "
            f"Kattaroq video uchun sayt yoki ilovadan foydalaning."
        )
        return

    status_msg = await message.answer("⬇️ Video qabul qilinmoqda...")
    local_tmp = None
    try:
        bot = message.bot
        tg_file = await bot.get_file(file_id)
        file_path = tg_file.file_path

        # Lokal Bot API server rejimida fayl umumiy volume'da (diskda) turadi
        if settings.TELEGRAM_API_URL and file_path and os.path.isfile(file_path):
            src_path = file_path
        else:
            # Bulut rejimi — faylni diskка yuklab olamiz (RAM ga emas)
            local_tmp = TMP_DIR / f"{uuid.uuid4().hex}.mp4"
            await bot.download(tg_file, destination=local_tmp)
            src_path = str(local_tmp)

        await _run_dubbing(message, status_msg, from_file=src_path)
    except TelegramBadRequest as exc:
        if "file is too big" in str(exc).lower():
            await status_msg.edit_text(
                "⚠️ Telegram bu faylni botga bermaydi (juda katta). "
                "Lokal Bot API server yoqilmagan bo'lsa, bot faqat 20MB oladi.\n"
                "Katta video uchun sayt/ilovadan foydalaning."
            )
        else:
            await status_msg.edit_text(f"❌ Telegram xatosi: <code>{str(exc)[:200]}</code>")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Video handler xatosi")
        await status_msg.edit_text(f"❌ Xatolik: <code>{str(exc)[:300]}</code>")
    finally:
        if local_tmp:
            Path(local_tmp).unlink(missing_ok=True)


@router.message(F.text.regexp(r"https?://"))
async def on_link(message: Message) -> None:
    """Havola (YouTube va boshqalar) kelganda backend o'zi yuklab oladi."""
    url = message.text.strip()
    status_msg = await message.answer("🔗 Havola qabul qilindi, ishlov berilmoqda...")
    try:
        user = message.from_user
        resp = await backend.submit_dub_url(
            url=url,
            voice="auto",
            external_id=str(user.id),
            username=user.username,
            full_name=user.full_name,
        )
        await _poll_and_send(message, status_msg, resp["task_id"], resp.get("eta_text"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Link handler xatosi")
        await status_msg.edit_text(f"❌ Xatolik: <code>{str(exc)[:300]}</code>")


async def _run_dubbing(message: Message, status_msg: Message, from_file: str) -> None:
    """Faylni backendga oqim orqali yuboradi va natijani qaytaradi."""
    await status_msg.edit_text("🚀 Serverga yuborilmoqda...")
    user = message.from_user
    resp = await backend.submit_dub_file(
        file_path=from_file,
        voice="auto",
        external_id=str(user.id),
        username=user.username,
        full_name=user.full_name,
    )
    await _poll_and_send(message, status_msg, resp["task_id"], resp.get("eta_text"))


async def _poll_and_send(message: Message, status_msg: Message, task_id: str, eta: str | None = None) -> None:
    """Statusni kuzatadi va tayyor videoni oqim orqali qaytaradi."""
    if eta:
        await status_msg.edit_text(f"⏱ Taxminiy vaqt: <b>{eta}</b>\n\n⚙️ Ishlov boshlandi...")
    final = await _poll_until_done(task_id, status_msg, eta)
    if final is None:
        return

    await status_msg.edit_text("⬇️ Tayyor video tayyorlanmoqda...")
    out_path = TMP_DIR / f"dubbed_{task_id}.mp4"
    try:
        await backend.download_to_file(task_id, out_path)
        await message.bot.send_video(
            chat_id=message.chat.id,
            video=FSInputFile(out_path, filename="dubbed.mp4"),
            caption="✅ <b>Tayyor!</b> Video o'zbek tiliga dublyaj qilindi.",
        )
        await status_msg.delete()
    finally:
        out_path.unlink(missing_ok=True)


async def _poll_until_done(task_id: str, status_msg: Message, eta: str | None = None) -> dict | None:
    waited, last_stage = 0, ""
    eta_line = f"\n⏱ Taxminiy vaqt: {eta}" if eta else ""
    while waited < settings.POLL_TIMEOUT:
        await asyncio.sleep(settings.POLL_INTERVAL)
        waited += settings.POLL_INTERVAL

        data = await backend.get_status(task_id)
        status = data.get("status")
        stage = data.get("stage", "")
        progress = data.get("progress", 0)

        if status == "completed":
            return data
        if status == "failed":
            await status_msg.edit_text(
                f"❌ Render xatolik bilan tugadi:\n<code>{data.get('error', 'nomaʼlum')[:300]}</code>"
            )
            return None

        if stage != last_stage:
            last_stage = stage
            label = STAGE_LABELS.get(stage, "⚙️ Ishlanmoqda...")
            await status_msg.edit_text(f"{label}\n\n📊 Progress: {progress}%{eta_line}")

    await status_msg.edit_text("⌛ Vaqt tugadi. Iltimos keyinroq urinib ko'ring.")
    return None
