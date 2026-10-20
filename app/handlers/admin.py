import psutil
import redis
from rq import Queue
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from app.config import settings
from app.database.models import ConversionJob, JobStatus, User
from app.database.session import AsyncSessionLocal

router = Router(name="admin_router")
redis_conn = redis.from_url(settings.REDIS_URL)
task_queue = Queue("pdf_jobs", connection=redis_conn)


@router.message(Command("admin"))
async def cmd_admin_stats(message: Message):
    if not message.from_user or message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ Unauthorized access.")
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

    stats_text = (
        "📊 <b>Administrator System Telemetry</b>\n\n"
        f"👥 <b>Total Registered Users:</b> <code>{total_users or 0}</code>\n"
        f"⚙️ <b>Total Jobs Executed:</b> <code>{total_jobs or 0}</code>\n"
        f"✅ <b>Completed Jobs:</b> <code>{completed_jobs or 0}</code>\n"
        f"❌ <b>Failed Jobs:</b> <code>{failed_jobs or 0}</code>\n"
        f"⏱ <b>Avg Execution Time:</b> <code>{int(avg_time or 0)} ms</code>\n"
        f"📥 <b>Pending Queue Size:</b> <code>{len(task_queue)}</code>\n\n"
        "🖥 <b>Server Resources</b>\n"
        f"• CPU Usage: <code>{cpu_pct}%</code>\n"
        f"• RAM Usage: <code>{mem.percent}% ({mem.used // (1024*1024)} MB / {mem.total // (1024*1024)} MB)</code>\n"
        f"• Temp Disk Free: <code>{disk.free // (1024*1024)} MB</code>"
    )
    await message.answer(stats_text)
