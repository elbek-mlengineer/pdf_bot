import asyncio
from collections.abc import Callable

from redis import Redis
from redis.exceptions import WatchError
from rq import Queue
from rq.job import Job

from app.config import settings
from app.i18n import tr

queue = Queue("pdf_jobs", connection=Redis.from_url(settings.REDIS_URL))


def _enqueue(function: Callable, args: tuple) -> Job:
    timeout = settings.CONVERSION_TIMEOUT_SECONDS
    job = queue.create_job(function, args=args, timeout=timeout, ttl=timeout)
    with queue.connection.pipeline() as pipe:
        while True:
            try:
                pipe.watch(queue.key)
                if pipe.llen(queue.key) >= settings.MAX_QUEUE_SIZE:
                    raise RuntimeError(tr("queue_full"))
                pipe.multi()
                queue.enqueue_job(job, pipeline=pipe)
                pipe.execute()
                return job
            except WatchError:
                continue


async def enqueue_conversion(function: Callable, *args) -> Job:
    return await asyncio.to_thread(_enqueue, function, args)
