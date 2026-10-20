from sqlalchemy import func, select
from app.database.models import ConversionJob, JobStatus, User, UserSettings
from app.database.session import AsyncSessionLocal


class Repository:
    @staticmethod
    async def upsert_user(
        telegram_id: int, username: str | None, first_name: str, last_name: str | None
    ) -> None:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, telegram_id)
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                )
                session.add(user)
                session.add(UserSettings(user_id=telegram_id))
                await session.commit()

    @staticmethod
    async def get_user_settings(telegram_id: int) -> UserSettings:
        async with AsyncSessionLocal() as session:
            prefs = await session.get(UserSettings, telegram_id)
            if not prefs:
                prefs = UserSettings(user_id=telegram_id, page_size="A4", orientation="portrait", margin=18)
                session.add(prefs)
                await session.commit()
                await session.refresh(prefs)
            return prefs

    @staticmethod
    async def update_user_settings(
        telegram_id: int, page_size: str | None = None, orientation: str | None = None
    ) -> UserSettings:
        async with AsyncSessionLocal() as session:
            prefs = await session.get(UserSettings, telegram_id)
            if not prefs:
                prefs = UserSettings(user_id=telegram_id)
                session.add(prefs)
            if page_size:
                prefs.page_size = page_size
            if orientation:
                prefs.orientation = orientation
            await session.commit()
            await session.refresh(prefs)
            return prefs

    @staticmethod
    async def count_active_user_jobs(telegram_id: int) -> int:
        async with AsyncSessionLocal() as session:
            count = await session.scalar(
                select(func.count(ConversionJob.id)).where(
                    ConversionJob.user_id == telegram_id,
                    ConversionJob.status.in_([JobStatus.QUEUED.value, JobStatus.PROCESSING.value]),
                )
            )
            return count or 0

    @staticmethod
    async def create_job(job_id: str, user_id: int, job_type: str) -> None:
        async with AsyncSessionLocal() as session:
            session.add(
                ConversionJob(
                    id=job_id,
                    user_id=user_id,
                    job_type=job_type,
                    status=JobStatus.QUEUED.value,
                )
            )
            await session.commit()

    @staticmethod
    async def update_job(
        job_id: str,
        status: JobStatus,
        execution_time_ms: int | None = None,
        error_message: str | None = None,
    ) -> None:
        async with AsyncSessionLocal() as session:
            job = await session.get(ConversionJob, job_id)
            if job:
                job.status = status.value
                if execution_time_ms is not None:
                    job.execution_time_ms = execution_time_ms
                if error_message is not None:
                    job.error_message = error_message[:500]
                await session.commit()
