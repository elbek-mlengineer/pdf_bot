from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="🖼 Images to PDF"),
            KeyboardButton(text="📝 Text to PDF"),
        ],
        [
            KeyboardButton(text="📄 Convert Document to PDF"),
            KeyboardButton(text="📚 Merge PDF Files"),
        ],
        [
            KeyboardButton(text="🛠 PDF Tools"),
            KeyboardButton(text="⚙️ Settings"),
        ],
        [
            KeyboardButton(text="❓ Help"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, selective=True)
