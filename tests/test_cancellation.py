import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from rq.job import JobStatus

from app.bot import dp
from app.queue.cancellation import CancelActiveConversion, ConversionCancelled, cancellation_scope
from app.queue.local import run_local
from app.queue.wait import wait_for_job


async def test_cancel_button_signals_session_before_fsm_lock():
    middleware = CancelActiveConversion(Mock())
    middleware.fsm.resolve_event_context.return_value.key = "session"
    update = Mock()
    update.callback_query.data = "action:cancel"
    update.callback_query.answer = AsyncMock()
    handler = AsyncMock()
    chain = list(dp.update.outer_middleware)
    assert next(i for i, item in enumerate(chain) if isinstance(item, CancelActiveConversion)) < chain.index(dp.fsm)
    with cancellation_scope("session") as signal:
        await middleware(handler, update, {"bot": Mock()})
        assert signal.is_set()
    handler.assert_not_awaited()


@pytest.mark.parametrize("started", [False, True])
async def test_cancel_rq_job(started):
    signal = asyncio.Event()
    signal.set()
    job = Mock()
    job.get_status.side_effect = [JobStatus.STARTED, JobStatus.STOPPED] if started else [JobStatus.QUEUED]
    with patch("app.queue.wait.Queue") as queue, patch("app.queue.wait.send_stop_job_command") as stop:
        queue.return_value.remove.return_value = 1
        with pytest.raises(ConversionCancelled):
            await wait_for_job(job, 2, signal)
        if started:
            stop.assert_called_once_with(job.connection, job.id)
            assert job.get_status.call_count == 2
        else:
            job.cancel.assert_called_once()


async def test_cancel_local_conversion_reaps_process(tmp_path):
    signal = asyncio.Event()
    signal.set()
    out = tmp_path / "cancelled.pdf"
    with pytest.raises(ConversionCancelled):
        await run_local("text", ["hello", str(out), "Document"], signal)
    assert not out.exists()

async def test_cancel_command_reaches_active_conversion():
    from aiogram.types import Update
    from app.bot import bot

    update = Update.model_validate({
        "update_id": 1,
        "message": {
            "message_id": 1, "date": 0, "chat": {"id": 9, "type": "private"},
            "from": {"id": 9, "is_bot": False, "first_name": "Test"}, "text": "/cancel",
        },
    }, context={"bot": bot})
    middleware = CancelActiveConversion(Mock())
    middleware.fsm.resolve_event_context.return_value.key = "session"
    with cancellation_scope("session") as signal, patch.object(type(update.message), "answer", new_callable=AsyncMock):
        await middleware(AsyncMock(), update, {"bot": bot})
        assert signal.is_set()
