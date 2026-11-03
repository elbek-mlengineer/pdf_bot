import shutil
import time
import uuid
from pathlib import Path
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Document, FSInputFile, Message
from rq import Queue
import redis

from app.bot import bot
from app.config import settings
from app.database.models import JobStatus, JobType
from app.database.repositories import Repository
from app.queue.tasks import run_doc_to_pdf_job
from app.queue.wait import wait_for_job
from app.utils.file_validator import FileValidationError, FileValidator
from app.utils.logger import logger

router = Router(name="documents_router")
redis_conn = redis.from_url(settings.REDIS_URL)
task_queue = Queue("pdf_jobs", connection=redis_conn)


class DocumentFlow(StatesGroup):
    waiting_for_doc = State()


@router.message(F.text == "📄 Convert Document to PDF")
async def start_doc_conversion(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(DocumentFlow.waiting_for_doc)
    await message.answer(
        "📄 <b>Document to PDF Converter</b>\n\n"
        "Upload your Office or text document:\n"
        "• Supported: <b>DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, RTF, TXT, CSV, HTML</b>\n"
        f"• Max file size: <b>{settings.MAX_FILE_SIZE_MB} MB</b>"
    )


@router.message(DocumentFlow.waiting_for_doc, F.document)
async def process_document_upload(message: Message, state: FSMContext):
    doc: Document = message.document
    if doc.file_size and doc.file_size > settings.max_file_size_bytes:
        await message.answer(f"❌ File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB.")
        return

    active_count = await Repository.count_active_user_jobs(message.from_user.id)
    if active_count >= settings.MAX_CONCURRENT_JOBS_PER_USER:
        await message.answer("⚠️ You already have active conversions in progress. Please wait.")
        return

    job_id = str(uuid.uuid4())
    job_dir = settings.TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    safe_name = FileValidator.sanitize_filename(doc.file_name or "document.docx")
    target_path = job_dir / safe_name

    status_msg = await message.answer("📥 Downloading and validating document...")
    await bot.download(doc.file_id, destination=target_path)

    try:
        FileValidator.validate_document(target_path, settings.max_file_size_bytes)
    except FileValidationError as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        await status_msg.edit_text(f"❌ Validation failed: {e}")
        return

    await status_msg.edit_text("⚙️ Converting document to PDF via LibreOffice...")
    start_ts = time.perf_counter()
    await Repository.create_job(job_id, message.from_user.id, JobType.DOC_TO_PDF.value)

    try:
        await Repository.update_job(job_id, JobStatus.PROCESSING)
        out_dir = job_dir / "converted"
        job = task_queue.enqueue(
            run_doc_to_pdf_job,
            args=(str(target_path), str(out_dir)),
            ttl=settings.CONVERSION_TIMEOUT_SECONDS,
            job_timeout=settings.CONVERSION_TIMEOUT_SECONDS,
        )

        await wait_for_job(job, settings.CONVERSION_TIMEOUT_SECONDS)

        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        converted_pdf_path = Path(job.result)
        out_file = FSInputFile(str(converted_pdf_path), filename=f"{Path(safe_name).stem}.pdf")
        await status_msg.delete()
        await message.answer_document(
            document=out_file,
            caption=f"✅ Document converted to PDF in {elapsed_ms} ms.",
        )
        await Repository.update_job(job_id, JobStatus.COMPLETED, execution_time_ms=elapsed_ms)

    except Exception as exc:
        logger.error("Document conversion failed: %s", exc)
        await message.answer(f"❌ Conversion error: {exc}")
        await Repository.update_job(job_id, JobStatus.FAILED, error_message=str(exc))
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        await state.clear()
