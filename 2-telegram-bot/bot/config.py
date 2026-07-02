"""Bot sozlamalari. AI kalitlari YO'Q — faqat backend manzili."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str
    # Markaziy FastAPI backend manzili
    BACKEND_URL: str = "http://localhost:8000"
    # Statusni tekshirish oralig'i (soniya) va maksimal kutish
    POLL_INTERVAL: int = 5
    POLL_TIMEOUT: int = 21600  # 6 soat (uzun videolar uchun)
    # Telegram bot orqali qabul qilinadigan maksimal video (MB).
    # DIQQAT: oddiy Bot API getFile orqali faqat ~20MB yuklab olish mumkin.
    # 2000MB (2GB) gacha uchun O'ZINGIZNING lokal Bot API serveringiz kerak
    # (TELEGRAM_API_URL ni sozlang). Telegram hech qachon 5GB ga ruxsat bermaydi —
    # katta videolar uchun Web yoki Mobil ilovadan foydalaning.
    MAX_VIDEO_MB: int = 2000
    # Lokal Bot API server manzili (bo'sh bo'lsa rasmiy api.telegram.org ishlatiladi)
    TELEGRAM_API_URL: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
