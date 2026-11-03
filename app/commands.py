from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat

from app.i18n import LANGUAGES, current_language, tr


def user_commands(language: str) -> list[BotCommand]:
    token = current_language.set(language)
    try:
        return [
            BotCommand(command=name, description=tr(f"command_{name}"))
            for name in ("start", "rename", "settings", "language", "help", "cancel")
        ]
    finally:
        current_language.reset(token)


async def register_commands(bot: Bot) -> None:
    await bot.set_my_commands(user_commands("en"))
    for language in LANGUAGES:
        await bot.set_my_commands(user_commands(language), language_code=language)


async def set_private_commands(bot: Bot, chat_id: int, language: str) -> None:
    await bot.set_my_commands(user_commands(language), scope=BotCommandScopeChat(chat_id=chat_id))
