from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.i18n import tr


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text=tr("menu_images")),
            KeyboardButton(text=tr("menu_text")),
        ],
        [
            KeyboardButton(text=tr("menu_document")),
            KeyboardButton(text=tr("menu_merge")),
        ],
        [
            KeyboardButton(text=tr("menu_tools")),
            KeyboardButton(text=tr("menu_settings")),
        ],
        [
            KeyboardButton(text=tr("menu_help")),
            KeyboardButton(text=tr("language")),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, selective=True)
