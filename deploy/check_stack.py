"""Compose release check. Run only against a dedicated test database."""
import asyncio
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import settings
from app.database.models import User, UserActivity
from app.database.repositories import Repository
from app.database.session import AsyncSessionLocal, init_db
from app.queue.submission import enqueue_conversion
from app.queue.tasks import run_doc_to_pdf_job
from app.queue.wait import wait_for_job


async def main():
    if os.environ.get("PDFBOT_RELEASE_TEST") != "1":
        raise RuntimeError("This check requires an isolated test stack")
    test_id = 700000001
    await init_db()
    if sys.argv[1] == "seed":
        await Repository.upsert_user(test_id, None, "Release", "Check")
        return
    if sys.argv[1] != "verify":
        raise ValueError("Use seed or verify")
    async with AsyncSessionLocal() as session:
        user = await session.get(User, test_id)
        assert user and user.first_name == "Release"
        assert (await session.get(UserActivity, test_id)).last_seen_at
    with TemporaryDirectory(dir=settings.TEMP_DIR) as directory:
        source = Path(directory) / "check.txt"
        source.write_text("Deployment check", encoding="utf-8")
        job = await enqueue_conversion(run_doc_to_pdf_job, str(source), str(source.parent / "out"))
        await wait_for_job(job, settings.CONVERSION_TIMEOUT_SECONDS)
        assert Path(job.result).read_bytes().startswith(b"%PDF-")
    print("Persisted user, activity and queued Office conversion verified.")


if __name__ == "__main__":
    asyncio.run(main())
