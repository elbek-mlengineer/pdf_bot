from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import LANGUAGES


def language_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=name, callback_data=f"lang:{code}")
                for code, name in LANGUAGES.items()
            ]
        ]
    )
