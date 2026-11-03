from unittest.mock import Mock

import pytest
from rq.exceptions import InvalidJobOperation
from rq.job import JobStatus

from app.queue.wait import wait_for_job


async def test_worker_never_picks_up_job():
    job = Mock()
    job.get_status.return_value = JobStatus.QUEUED
    with pytest.raises(RuntimeError, match="timed out"):
        await wait_for_job(job, timeout=0.02)


async def test_queue_entry_expires():
    job = Mock()
    job.get_status.side_effect = InvalidJobOperation("Missing job")
    with pytest.raises(RuntimeError, match="expired"):
        await wait_for_job(job, timeout=1)


async def test_finished_job_returns():
    job = Mock()
    job.get_status.return_value = JobStatus.FINISHED
    await wait_for_job(job, timeout=1)
