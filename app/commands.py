from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

from app.config import settings
from app.i18n import LANGUAGES, current_language, tr


def user_commands(language: str, *, admin: bool = False) -> list[BotCommand]:
    token = current_language.set(language)
    try:
        names = ["start", "rename", "settings", "language", "help", "cancel"]
        if admin:
            names.extend(["admin", "users"])
        return [
            BotCommand(command=name, description=tr(f"command_{name}"))
            for name in names
        ]
    finally:
        current_language.reset(token)


async def register_commands(bot: Bot) -> None:
    await bot.set_my_commands(user_commands("en"))
    for language in LANGUAGES:
        await bot.set_my_commands(user_commands(language), language_code=language)


async def set_private_commands(bot: Bot, chat_id: int, language: str) -> None:
    await bot.set_my_commands(
        user_commands(language, admin=chat_id in settings.ADMIN_IDS),
        scope=BotCommandScopeChat(chat_id=chat_id),
    )
