from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageCaption,
    EditMessageText,
    SendDocument,
    SendMessage,
)

from app.middlewares.signature import BotSignature


@pytest.mark.parametrize(
    ("method", "field", "expected"),
    [
        (SendMessage(chat_id=1, text="<b>Salom</b>"), "text", "<b>Salom</b>\n\n@ExampleBot"),
        (
            EditMessageText(chat_id=1, message_id=1, text="Tayyor\n\n@ExampleBot"),
            "text",
            "Tayyor\n\n@ExampleBot",
        ),
        (SendDocument(chat_id=1, document="file_id"), "caption", "@ExampleBot"),
        (
            SendDocument(chat_id=1, document="file_id", caption="Готово"),
            "caption",
            "Готово\n\n@ExampleBot",
        ),
        (
            EditMessageCaption(chat_id=1, message_id=1, caption="Done"),
            "caption",
            "Done\n\n@ExampleBot",
        ),
    ],
)
async def test_signed_messages(method, field, expected):
    bot = AsyncMock()
    bot.me.return_value = SimpleNamespace(username="ExampleBot")
    send = AsyncMock()
    await BotSignature()(send, bot, method)
    outgoing = send.await_args.args[1]
    assert getattr(outgoing, field) == expected


async def test_callback_notification_is_unchanged():
    bot, send = AsyncMock(), AsyncMock()
    method = AnswerCallbackQuery(callback_query_id="id", text="OK")
    await BotSignature()(send, bot, method)
    send.assert_awaited_once_with(bot, method)
    bot.me.assert_not_awaited()
