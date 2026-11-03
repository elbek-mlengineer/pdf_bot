import shutil
import time
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Document, FSInputFile, Message

from app.bot import bot
from app.config import settings
from app.database.models import JobStatus, JobType
from app.database.repositories import Repository
from app.i18n import labels, tr
from app.keyboards.inline import get_merge_action_keyboard
from app.queue.cancellation import ConversionCancelled, cancellation_scope
from app.queue.submission import enqueue_conversion
from app.queue.tasks import run_merge_pdf_job
from app.queue.wait import wait_for_job
from app.utils.file_validator import FileValidationError, FileValidator
from app.utils.logger import logger
from app.utils.session_files import clear_session

router = Router(name="merge_router")


class MergeFlow(StatesGroup):
    collecting_pdfs = State()


@router.message(F.text.in_(labels("menu_merge")))
async def start_pdf_merge(message: Message, state: FSMContext):
    await clear_session(state)
    job_id = str(uuid.uuid4())
    job_dir = settings.TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    await state.update_data(job_id=job_id, job_dir=str(job_dir), files=[])
    await state.set_state(MergeFlow.collecting_pdfs)

    await message.answer(tr("merge_prompt", settings.MAX_PDF_MERGE_COUNT))


@router.message(MergeFlow.collecting_pdfs, F.document)
async def handle_pdf_for_merge(message: Message, state: FSMContext):
    data = await state.get_data()
    file_list: list[str] = data.get("files", [])

    if len(file_list) >= settings.MAX_PDF_MERGE_COUNT:
        await message.answer(tr("merge_limit", settings.MAX_PDF_MERGE_COUNT))
        return

    doc: Document = message.document
    if doc.file_size and doc.file_size > settings.max_file_size_bytes:
        await message.answer(tr("size_limit", settings.MAX_FILE_SIZE_MB))
        return

    job_dir = Path(data["job_dir"])
    target_path = job_dir / f"doc_{len(file_list):03d}.pdf"
    await bot.download(doc.file_id, destination=target_path)

    try:
        pages = FileValidator.validate_pdf(target_path, settings.max_file_size_bytes)
        file_list.append(str(target_path))
        await state.update_data(files=file_list)

        await message.answer(
            tr("pdf_added", len(file_list), pages),
            reply_markup=get_merge_action_keyboard(len(file_list)),
        )
    except FileValidationError as e:
        target_path.unlink(missing_ok=True)
        await message.answer(tr("rejected", e))


@router.callback_query(MergeFlow.collecting_pdfs, F.data == "merge:execute")
async def execute_merge(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    file_list: list[str] = data.get("files", [])
    job_id = data.get("job_id")
    job_dir = Path(data.get("job_dir"))

    if len(file_list) < 2:
        await callback.answer(tr("need_two"), show_alert=True)
        return

    await callback.message.edit_text(tr("merge_work"))
    output_pdf = job_dir / "merged_document.pdf"
    start_ts = time.perf_counter()
    await Repository.create_job(job_id, callback.from_user.id, JobType.MERGE_PDF.value)

    try:
        await Repository.update_job(job_id, JobStatus.PROCESSING)
        job = await enqueue_conversion(run_merge_pdf_job, file_list, str(output_pdf))

        with cancellation_scope(state.key) as signal:
            await wait_for_job(job, settings.CONVERSION_TIMEOUT_SECONDS, signal)

        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        merged_file = FSInputFile(str(output_pdf), filename="Merged_Document.pdf")
        await callback.message.answer_document(
            document=merged_file,
            caption=tr("merged", len(file_list), elapsed_ms),
        )
        await Repository.update_job(job_id, JobStatus.COMPLETED, execution_time_ms=elapsed_ms)

    except ConversionCancelled:
        await Repository.update_job(job_id, JobStatus.CANCELLED)
        await callback.message.answer(tr("cancelled"))
    except Exception as exc:
        logger.error("Merge error: %s", exc)
        await callback.message.answer(tr("merge_error", exc))
        await Repository.update_job(job_id, JobStatus.FAILED, error_message=str(exc))
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        await state.clear()
        await callback.answer()
