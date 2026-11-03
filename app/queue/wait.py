import asyncio

from rq.exceptions import InvalidJobOperation
from rq.job import Job, JobStatus
from rq import Queue
from rq.command import send_stop_job_command

from app.queue.cancellation import ConversionCancelled


def request_stop(job, status):
    if status == JobStatus.QUEUED:
        queue = Queue(job.origin, connection=job.connection)
        if queue.remove(job):
            job.cancel()
            return True
    if status == JobStatus.STARTED:
        send_stop_job_command(job.connection, job.id)
    return False


async def wait_for_job(job: Job, timeout: int, signal: asyncio.Event | None = None) -> None:
    """Allow one timeout interval in the queue and one for execution."""
    try:
        async with asyncio.timeout(2 * timeout):
            while True:
                status = await asyncio.to_thread(job.get_status)
                if signal is not None and signal.is_set():
                    if status in (JobStatus.FINISHED, JobStatus.STOPPED, JobStatus.CANCELED, JobStatus.FAILED):
                        raise ConversionCancelled
                    try:
                        removed = await asyncio.to_thread(request_stop, job, status)
                    except InvalidJobOperation:
                        removed = False  # Worker transitioned while the command was in flight.
                    if removed:
                        raise ConversionCancelled
                if status == JobStatus.FINISHED:
                    return
                if status in (JobStatus.FAILED, JobStatus.STOPPED, JobStatus.CANCELED):
                    raise RuntimeError("PDF processing failed or was stopped.")
                await asyncio.sleep(0.5)
    except InvalidJobOperation as exc:
        raise RuntimeError("The job expired or was removed. Please try again.") from exc
    except TimeoutError as exc:
        raise RuntimeError("PDF processing timed out. Please try again.") from exc
