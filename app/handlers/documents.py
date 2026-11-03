import asyncio
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Document, FSInputFile, Message

from app.bot import bot
from app.config import settings
from app.database.models import JobStatus, JobType
from app.database.repositories import Repository
from app.i18n import labels, tr
from app.queue.cancellation import ConversionCancelled, cancellation_scope
from app.queue.submission import enqueue_conversion
from app.queue.tasks import run_doc_to_pdf_job
from app.queue.wait import wait_for_job
from app.utils.file_validator import FileValidationError, FileValidator
from app.utils.logger import logger
from app.utils.session_files import clear_session

router = Router(name="documents_router")


class DocumentFlow(StatesGroup):
    waiting_for_doc = State()


@router.message(F.text.in_(labels("menu_document")))
async def start_doc_conversion(message: Message, state: FSMContext):
    await clear_session(state)
    await state.set_state(DocumentFlow.waiting_for_doc)
    await message.answer(tr("document_prompt", settings.MAX_FILE_SIZE_MB))


@router.message(DocumentFlow.waiting_for_doc, F.document)
async def process_document_upload(message: Message, state: FSMContext):
    doc: Document = message.document
    if doc.file_size and doc.file_size > settings.max_file_size_bytes:
        await message.answer(tr("size_max", settings.MAX_FILE_SIZE_MB))
        return

    with cancellation_scope(state.key) as signal:
        try:
            await _convert_document(message, state, doc, signal)
        except ConversionCancelled:
            await state.clear()
            await message.answer(tr("cancelled"))


async def _convert_document(
    message: Message, state: FSMContext, doc: Document, signal: asyncio.Event
):
    active_count = await Repository.count_active_user_jobs(message.from_user.id)
    if active_count >= settings.MAX_CONCURRENT_JOBS_PER_USER:
        await message.answer(tr("busy"))
        return

    job_id = str(uuid.uuid4())
    with TemporaryDirectory(dir=settings.TEMP_DIR, prefix=f"{job_id}_") as directory:
        await _process_file(message, state, doc, signal, job_id, Path(directory))


async def _process_file(message, state, doc, signal, job_id, job_dir):
    safe_name = FileValidator.sanitize_filename(doc.file_name or "document.docx")
    target_path = job_dir / safe_name

    try:
        status_msg = await message.answer(tr("downloading"))
        await download_or_cancel(doc.file_id, target_path, signal)
        FileValidator.validate_document(target_path, settings.max_file_size_bytes)
    except ConversionCancelled:
        raise
    except FileValidationError as e:
        await status_msg.edit_text(tr("invalid", e))
        return
    except Exception:
        await message.answer(tr("download_failed"))
        return

    await status_msg.edit_text(tr("document_work"))
    start_ts = time.perf_counter()
    await Repository.create_job(job_id, message.from_user.id, JobType.DOC_TO_PDF.value)
    try:
        await Repository.update_job(job_id, JobStatus.PROCESSING)
        out_dir = job_dir / "converted"
        if signal.is_set():
            raise ConversionCancelled
        job = await enqueue_conversion(run_doc_to_pdf_job, str(target_path), str(out_dir))

        await wait_for_job(job, settings.CONVERSION_TIMEOUT_SECONDS, signal)

        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        converted_pdf_path = Path(job.result)
        out_file = FSInputFile(str(converted_pdf_path), filename=f"{Path(safe_name).stem}.pdf")
        await status_msg.delete()
        if signal.is_set():
            raise ConversionCancelled
        await message.answer_document(
            document=out_file,
            caption=tr("document_done", elapsed_ms),
        )
        await Repository.update_job(job_id, JobStatus.COMPLETED, execution_time_ms=elapsed_ms)

    except ConversionCancelled:
        await Repository.update_job(job_id, JobStatus.CANCELLED)
        await message.answer(tr("cancelled"))
    except Exception as exc:
        logger.error("Document conversion failed: %s", exc)
        await message.answer(tr("conversion_error", exc))
        await Repository.update_job(job_id, JobStatus.FAILED, error_message=str(exc))
    finally:
        await state.clear()


async def download_or_cancel(file_id: str, destination: Path, signal: asyncio.Event) -> None:
    if signal.is_set():
        raise ConversionCancelled
    download = asyncio.create_task(bot.download(file_id, destination=destination))
    cancellation = asyncio.create_task(signal.wait())
    try:
        await asyncio.wait((download, cancellation), return_when=asyncio.FIRST_COMPLETED)
        if signal.is_set():
            raise ConversionCancelled
        await download
    finally:
        cancellation.cancel()
        download.cancel()
        await asyncio.gather(download, cancellation, return_exceptions=True)
