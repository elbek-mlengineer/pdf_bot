import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from redis.exceptions import WatchError

from app import main
from app.handlers import documents, text
from app.queue import submission
from app.queue.cancellation import CancelActiveConversion


async def test_switching_flow_removes_previous_files(tmp_path):
    folder = tmp_path / "previous"
    folder.mkdir()
    (folder / "upload.pdf").write_bytes(b"private")
    state = AsyncMock()
    state.get_data.return_value = {"job_dir": str(folder)}
    await text.start_text_to_pdf(AsyncMock(), state)
    assert not folder.exists()
    state.clear.assert_awaited_once()
    state.set_state.assert_awaited_once_with(text.TextFlow.waiting_for_text)


async def test_restart_keeps_pending_updates():
    with (
        patch.object(main, "bot", AsyncMock()) as bot,
        patch.object(main, "dp") as dp,
        patch.object(main, "init_db", AsyncMock()),
    ):
        dp.start_polling = AsyncMock()
        await main.main()
        bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=False)
        dp.start_polling.assert_awaited_once()


async def test_cancel_during_download(tmp_path, monkeypatch):
    monkeypatch.setattr(documents.settings, "TEMP_DIR", tmp_path)
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def download(file_id, destination):
        destination.write_bytes(b"partial")
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    msg = AsyncMock()
    msg.document = Mock(file_size=7, file_id="upload", file_name="example.docx")
    state = AsyncMock()
    middleware = CancelActiveConversion(Mock())
    middleware.fsm.resolve_event_context.return_value.key = state.key
    middleware.command = AsyncMock(return_value=True)
    update = Mock(callback_query=None, message=AsyncMock())
    with (
        patch.object(documents, "bot", Mock(download=download)),
        patch.object(documents.Repository, "count_active_user_jobs", AsyncMock(return_value=0)),
        patch.object(documents, "enqueue_conversion", AsyncMock()) as enqueue,
    ):
        task = asyncio.create_task(documents.process_document_upload(msg, state))
        await asyncio.wait_for(started.wait(), 2)
        await middleware(AsyncMock(), update, {"bot": Mock()})
        await asyncio.wait_for(task, 2)
        assert stopped.is_set()
        assert not list(tmp_path.iterdir())
        enqueue.assert_not_awaited()
        state.clear.assert_awaited_once()


def test_queue_capacity_is_rechecked_after_concurrent_enqueue(monkeypatch):
    queue = MagicMock()
    monkeypatch.setattr(submission, "queue", queue)
    monkeypatch.setattr(submission.settings, "MAX_QUEUE_SIZE", 2)
    pipe = queue.connection.pipeline.return_value.__enter__.return_value
    pipe.llen.side_effect = [1, 2]
    pipe.execute.side_effect = WatchError()
    with pytest.raises(RuntimeError, match="queue is full"):
        submission._enqueue(str, (1,))
    assert pipe.watch.call_count == 2
    pipe.execute.assert_called_once()


def test_available_queue_slot_is_committed(monkeypatch):
    queue = MagicMock()
    monkeypatch.setattr(submission, "queue", queue)
    pipe = queue.connection.pipeline.return_value.__enter__.return_value
    pipe.llen.return_value = 0
    job = submission._enqueue(str, (1,))
    queue.enqueue_job.assert_called_once_with(job, pipeline=pipe)
    pipe.execute.assert_called_once()


async def test_session_survives_storage_restart(tmp_path):
    from aiogram.fsm.storage.base import StorageKey
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.database.fsm import SessionStorage
    from app.database.models import BotSession

    url = f"sqlite+aiosqlite:///{(tmp_path / 'sessions.db').as_posix()}"
    key = StorageKey(bot_id=1, chat_id=2, user_id=3)
    first = create_async_engine(url)
    try:
        async with first.begin() as connection:
            await connection.run_sync(BotSession.__table__.create)
        storage = SessionStorage(async_sessionmaker(first))
        await storage.set_data(key, {"files": ["first.pdf"]})
        await storage.set_state(key, "collecting")
    finally:
        await first.dispose()

    second = create_async_engine(url)
    try:
        storage = SessionStorage(async_sessionmaker(second))
        assert await storage.get_state(key) == "collecting"
        assert await storage.get_data(key) == {"files": ["first.pdf"]}
        await storage.set_state(key, None)
        await storage.set_data(key, {})
        assert await storage.get_state(key) is None
        assert await storage.get_data(key) == {}
    finally:
        await second.dispose()
