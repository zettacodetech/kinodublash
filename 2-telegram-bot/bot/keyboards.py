"""Inline klaviaturalar."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def voice_keyboard(file_id: str) -> InlineKeyboardMarkup:
    """Ovoz turini tanlash tugmalari. callback_data ichida file_id uzatiladi."""
    builder = InlineKeyboardBuilder()
    builder.button(text="👨 Erkak ovozi", callback_data=f"voice:male:{file_id}")
    builder.button(text="👩 Ayol ovozi", callback_data=f"voice:female:{file_id}")
    builder.adjust(2)
    return builder.as_markup()
