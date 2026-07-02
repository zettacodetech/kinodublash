"""Taxminiy ishlov vaqti (ETA) hisoblash va o'zbekcha formatlash."""
from .config import settings


def estimate_seconds(duration_seconds: float | None) -> int | None:
    """Video davomiyligidan taxminiy ishlov vaqtini (soniya) hisoblaydi."""
    if not duration_seconds or duration_seconds <= 0:
        return None
    return int(duration_seconds * settings.ETA_FACTOR + settings.ETA_BASE_SECONDS)


def format_uz(seconds: int | None) -> str | None:
    """Soniyani o'zbekcha matnga aylantiradi: '~2 soat 15 daqiqa'."""
    if not seconds or seconds <= 0:
        return None
    minutes = max(1, round(seconds / 60))
    if minutes < 60:
        return f"~{minutes} daqiqa"
    hours, mins = divmod(minutes, 60)
    return f"~{hours} soat {mins} daqiqa" if mins else f"~{hours} soat"
