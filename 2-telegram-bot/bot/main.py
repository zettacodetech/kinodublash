"""Telegram bot kirish nuqtasi (Aiogram 3.x, long polling)."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import settings
from .handlers import backend, router

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    # Katta fayllar (2GB gacha) uchun lokal Bot API server. is_local=True bo'lganda
    # getFile natijasi lokal fayl yo'lini qaytaradi (umumiy volume orqali o'qiladi).
    session = None
    if settings.TELEGRAM_API_URL:
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(settings.TELEGRAM_API_URL.rstrip("/"), is_local=True)
        )
        logging.info("Lokal Bot API server ishlatilmoqda: %s", settings.TELEGRAM_API_URL)

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await backend.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
