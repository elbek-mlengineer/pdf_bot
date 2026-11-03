import json
from pathlib import Path
from string import Formatter
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.common import select_language
from app.i18n import LANGUAGES, current_language, labels, tr
from app.keyboards.main_menu import get_main_menu
from app.middlewares.language import LanguageMiddleware


def test_translations_have_matching_fields():
    folder = Path(__file__).resolve().parents[1] / "app" / "locales"

    def fields(code):
        messages = json.loads((folder / f"{code}.json").read_text(encoding="utf8"))
        return {
            key: sorted(field for _, field, _, _ in Formatter().parse(value) if field is not None)
            for key, value in messages.items()
        }

    assert fields("uz") == fields("ru") == fields("en")


@pytest.mark.parametrize("language", LANGUAGES)
async def test_selection_survives_cancel_and_rebuilds_menu(language):
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key=StorageKey(bot_id=1, chat_id=2, user_id=2))
    user = SimpleNamespace(id=2, first_name="Ali", language_code="fr")
    callback = SimpleNamespace(
        bot=SimpleNamespace(id=1),
        from_user=user,
        data=f"lang:{language}",
        answer=AsyncMock(),
        message=AsyncMock(),
    )
    middleware = LanguageMiddleware(storage)
    data = {"bot": callback.bot, "event_from_user": user}

    async def select(event, data):
        await select_language(callback, state)

    await middleware(select, callback, data)
    await state.clear()

    async def next_update(event, data):
        assert current_language.get() == language
        button = get_main_menu().keyboard[0][0].text
        assert button == tr("menu_images")
        assert button in labels("menu_images")
        assert (
            callback.message.answer.await_args.kwargs["reply_markup"].keyboard[0][0].text == button
        )

    await LanguageMiddleware(storage)(next_update, None, data)
    assert current_language.get() == "en"

async def test_slash_menu_registration():
    from app.commands import register_commands, set_private_commands

    bot = AsyncMock()
    await register_commands(bot)
    calls = bot.set_my_commands.await_args_list
    assert [c.kwargs.get("language_code") for c in calls] == [None, *LANGUAGES]
    for call in calls:
        assert [item.command for item in call.args[0]] == [
            "start", "rename", "settings", "language", "help", "cancel"
        ]
    await set_private_commands(bot, 123, "uz")
    private = bot.set_my_commands.await_args
    assert private.kwargs["scope"].chat_id == 123
    assert private.args[0][0].description == "Asosiy menyuni ochish"
