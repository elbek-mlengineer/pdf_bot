from html import escape

import psutil
import redis
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from rq import Queue
from sqlalchemy import func, select

from app.config import settings
from app.database.models import ConversionJob, JobStatus, User, UserActivity
from app.database.session import AsyncSessionLocal
from app.i18n import tr

router = Router(name="admin_router")
redis_conn = redis.from_url(settings.REDIS_URL)
task_queue = Queue("pdf_jobs", connection=redis_conn)


@router.message(Command("admin"))
async def cmd_admin_stats(message: Message):
    if not is_private_admin(message):
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
    await message.answer(stats_text + "\n\n/users")


def is_private_admin(message: Message) -> bool:
    return bool(
        message.chat.type == "private"
        and message.from_user
        and message.from_user.id in settings.ADMIN_IDS
    )


@router.message(Command("users"))
async def show_users(message: Message):
    if not is_private_admin(message):
        await message.answer(tr("unauthorized"))
        return
    parts = message.text.split(maxsplit=1)
    try:
        page = int(parts[1]) if len(parts) > 1 else 1
        if not 1 <= page <= 100000000:
            raise ValueError
    except ValueError:
        await message.answer("/users 1")
        return
    async with AsyncSessionLocal() as session:
        total = await session.scalar(select(func.count(User.telegram_id)))
        rows = (
            await session.execute(
                select(User, UserActivity.last_seen_at)
                .outerjoin(UserActivity, UserActivity.user_id == User.telegram_id)
                .order_by(User.created_at.desc(), User.telegram_id.desc())
                .offset((page - 1) * 8)
                .limit(8)
            )
        ).all()
    lines = [tr("user_directory", total, page)]
    for user, seen in rows:
        name = escape(" ".join(filter(None, (user.first_name, user.last_name))))
        handle = "@" + escape(user.username) if user.username else "—"
        lines.append(
            f"{name} · {handle} · <code>{user.telegram_id}</code>\n"
            + tr(
                "user_dates",
                user.created_at.strftime("%Y-%m-%d %H:%M"),
                seen.strftime("%Y-%m-%d %H:%M") if seen else "—",
            )
        )
    if page * 8 < total:
        lines.append(f"/users {page + 1}")
    await message.answer("\n\n".join(lines))
