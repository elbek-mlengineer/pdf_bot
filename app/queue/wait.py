import asyncio

from rq.exceptions import InvalidJobOperation
from rq.job import Job, JobStatus


async def wait_for_job(job: Job, timeout: int) -> None:
    """Allow one timeout interval in the queue and one for execution."""
    try:
        async with asyncio.timeout(2 * timeout):
            while True:
                status = await asyncio.to_thread(job.get_status)
                if status == JobStatus.FINISHED:
                    return
                if status in (JobStatus.FAILED, JobStatus.STOPPED, JobStatus.CANCELED):
                    raise RuntimeError("PDF processing failed or was stopped.")
                await asyncio.sleep(0.5)
    except InvalidJobOperation as exc:
        raise RuntimeError("The job expired or was removed. Please try again.") from exc
    except TimeoutError as exc:
        raise RuntimeError("PDF processing timed out. Please try again.") from exc
