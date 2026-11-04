from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.handlers.rename import TRANSFER_TIMEOUT, RenameFlow, receive_file, send_renamed_file


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        ("Hisobot", "Hisobot.xlsx"),
        ("Новый файл.xlsx", "Новый файл.xlsx"),
        ("archive.bin", "archive.bin"),
    ],
)
async def test_rename_delivers_same_bytes(tmp_path, monkeypatch, requested, expected):
    from app.config import settings

    monkeypatch.setattr(settings, "TEMP_DIR", tmp_path)
    payload = b"x" * (11 * 1024 * 1024)
    message = AsyncMock()
    message.document = SimpleNamespace(
        file_name="old.xlsx", file_id="original", file_size=len(payload)
    )
    state = AsyncMock()
    await receive_file(message, state)
    state.set_state.assert_awaited_once_with(RenameFlow.waiting_for_name)
    state.get_data.return_value = state.update_data.await_args.kwargs
    message.text = requested

    async def download(file_id, destination, timeout):
        assert timeout == TRANSFER_TIMEOUT
        if message.bot.download.await_count == 1:
            destination.write_bytes(b"partial")
            raise TimeoutError
        assert not destination.exists()
        assert file_id == "original"
        destination.write_bytes(payload)

    async def send(document, request_timeout):
        assert request_timeout == TRANSFER_TIMEOUT
        assert document.filename == expected
        assert document.path.read_bytes() == payload

    message.bot.download.side_effect = download
    message.answer_document = Mock(side_effect=lambda document, **kwargs: document)
    message.bot.side_effect = send
    await send_renamed_file(message, state)
    message.answer_document.assert_called_once()
    assert message.bot.download.await_count == 2
    state.clear.assert_awaited_once()
    assert not list(tmp_path.iterdir())


async def test_invalid_rename_keeps_file_for_retry():
    message = AsyncMock()
    message.text = "../bad.txt"
    state = AsyncMock()
    state.get_data.return_value = {"rename_file_id": "x", "original_name": "old.txt"}
    await send_renamed_file(message, state)
    message.bot.download.assert_not_awaited()
    state.clear.assert_not_awaited()


async def test_rename_rejects_oversized_cloud_file_before_asking_for_name():
    message = AsyncMock()
    message.bot.session.api.is_local = False
    message.document.file_size = 21 * 1024 * 1024
    state = AsyncMock()
    await receive_file(message, state)
    state.update_data.assert_not_awaited()
    assert "20" in message.answer.await_args.args[0]
