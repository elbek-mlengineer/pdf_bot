import psutil
import redis
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from rq import Queue
from sqlalchemy import func, select

from app.config import settings
from app.database.models import ConversionJob, JobStatus, User
from app.database.session import AsyncSessionLocal
from app.i18n import tr

router = Router(name="admin_router")
redis_conn = redis.from_url(settings.REDIS_URL)
task_queue = Queue("pdf_jobs", connection=redis_conn)


@router.message(Command("admin"))
async def cmd_admin_stats(message: Message):
    if not message.from_user or message.from_user.id not in settings.ADMIN_IDS:
        await message.answer(tr("unauthorized"))
        return

    async with AsyncSessionLocal() as session:
        total_users = await session.scalar(select(func.count(User.telegram_id)))
        total_jobs = await session.scalar(select(func.count(ConversionJob.id)))
        completed_jobs = await session.scalar(
            select(func.count(ConversionJob.id)).where(
                ConversionJob.status == JobStatus.COMPLETED.value
            )
        )
        failed_jobs = await session.scalar(
            select(func.count(ConversionJob.id)).where(
                ConversionJob.status == JobStatus.FAILED.value
            )
        )
        avg_time = await session.scalar(
            select(func.avg(ConversionJob.execution_time_ms)).where(
                ConversionJob.status == JobStatus.COMPLETED.value
            )
        )

    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(settings.TEMP_DIR))

    stats_text = tr(
        "admin_stats",
        total_users or 0,
        total_jobs or 0,
        completed_jobs or 0,
        failed_jobs or 0,
        int(avg_time or 0),
        len(task_queue),
        cpu_pct,
        mem.percent,
        mem.used // (1024 * 1024),
        mem.total // (1024 * 1024),
        disk.free // (1024 * 1024),
    )
    await message.answer(stats_text)
