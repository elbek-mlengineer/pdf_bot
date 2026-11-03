import shutil
import time
import uuid
from pathlib import Path
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Document, FSInputFile, Message
from rq import Queue
import redis

from app.bot import bot
from app.config import settings
from app.database.models import JobStatus, JobType
from app.database.repositories import Repository
from app.keyboards.inline import get_pdf_tools_keyboard
from app.queue.tasks import run_pdf_tool_job
from app.queue.wait import wait_for_job
from app.utils.file_validator import FileValidationError, FileValidator
from app.utils.logger import logger
from app.queue.cancellation import ConversionCancelled, cancellation_scope

router = Router(name="tools_router")
redis_conn = redis.from_url(settings.REDIS_URL)
task_queue = Queue("pdf_jobs", connection=redis_conn)


class ToolsFlow(StatesGroup):
    waiting_for_pdf = State()
    selecting_tool = State()
    waiting_for_page_range = State()
    waiting_for_metadata = State()


@router.message(F.text == "🛠 PDF Tools")
async def start_pdf_tools(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ToolsFlow.waiting_for_pdf)
    await message.answer(
        "🛠 <b>PDF Manipulation Tools</b>\n\n"
        "Upload a PDF file to access:\n"
        "• Compress PDF size\n"
        "• Add Page Numbers\n"
        "• Rotate Pages (90° / 180°)\n"
        "• Extract Specific Pages\n"
        "• Split All Pages into ZIP\n"
        "• Extract Embedded Images\n"
        "• Edit PDF Title & Author Metadata"
    )


@router.message(ToolsFlow.waiting_for_pdf, F.document)
async def receive_pdf_for_tools(message: Message, state: FSMContext):
    doc: Document = message.document
    if doc.file_size and doc.file_size > settings.max_file_size_bytes:
        await message.answer(f"❌ File exceeds {settings.MAX_FILE_SIZE_MB} MB limit.")
        return

    job_id = str(uuid.uuid4())
    job_dir = settings.TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_pdf = job_dir / "input.pdf"

    await bot.download(doc.file_id, destination=input_pdf)
    try:
        pages = FileValidator.validate_pdf(input_pdf, settings.max_file_size_bytes)
    except FileValidationError as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        await message.answer(f"❌ Invalid PDF: {e}")
        return

    await state.update_data(job_id=job_id, job_dir=str(job_dir), input_pdf=str(input_pdf), pages=pages)
    await state.set_state(ToolsFlow.selecting_tool)
    await message.answer(
        f"✅ PDF loaded ({pages} pages). Choose an action below:",
        reply_markup=get_pdf_tools_keyboard(),
    )


@router.callback_query(ToolsFlow.selecting_tool, F.data.startswith("tool:"))
async def handle_tool_selection(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    tool = parts[1]
    param = parts[2] if len(parts) > 2 else ""

    if tool == "extract_pages":
        await state.set_state(ToolsFlow.waiting_for_page_range)
        await callback.message.edit_text(
            "✂️ Send the page numbers or ranges you want to extract (e.g. <code>1-3, 5</code>):"
        )
        await callback.answer()
        return

    if tool == "metadata":
        await state.set_state(ToolsFlow.waiting_for_metadata)
        await callback.message.edit_text(
            "🏷 Send the new Title and Author separated by <code>|</code>\n"
            "Example: <code>Annual Report 2026 | FinTech Team</code>"
        )
        await callback.answer()
        return

    await callback.message.edit_text("⚙️ Processing your PDF...")
    await _run_tool_and_reply(callback.message, callback.from_user.id, state, tool, param)
    await callback.answer()


@router.message(ToolsFlow.waiting_for_page_range, F.text)
async def handle_page_range_input(message: Message, state: FSMContext):
    await _run_tool_and_reply(message, message.from_user.id, state, "extract_pages", message.text.strip())


@router.message(ToolsFlow.waiting_for_metadata, F.text)
async def handle_metadata_input(message: Message, state: FSMContext):
    await _run_tool_and_reply(message, message.from_user.id, state, "metadata", message.text.strip())


async def _run_tool_and_reply(
    message: Message, user_id: int, state: FSMContext, tool: str, param: str
):
    data = await state.get_data()
    job_id = data["job_id"]
    job_dir = Path(data["job_dir"])
    input_pdf = data["input_pdf"]

    is_zip = tool in ("split", "extract_images")
    ext = ".zip" if is_zip else ".pdf"
    out_path = job_dir / f"output_{tool}{ext}"

    start_ts = time.perf_counter()
    await Repository.create_job(job_id, user_id, JobType.TOOLS.value)

    try:
        await Repository.update_job(job_id, JobStatus.PROCESSING)
        job = task_queue.enqueue(
            run_pdf_tool_job,
            args=(tool, input_pdf, str(out_path), param),
            ttl=settings.CONVERSION_TIMEOUT_SECONDS,
            job_timeout=settings.CONVERSION_TIMEOUT_SECONDS,
        )

        with cancellation_scope(state.key) as signal:
            await wait_for_job(job, settings.CONVERSION_TIMEOUT_SECONDS, signal)

        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        out_file = FSInputFile(str(out_path), filename=f"Result_{tool}{ext}")
        await message.answer_document(
            document=out_file,
            caption=f"✅ PDF tool '{tool}' completed in {elapsed_ms} ms.",
        )
        await Repository.update_job(job_id, JobStatus.COMPLETED, execution_time_ms=elapsed_ms)

    except ConversionCancelled:
        await Repository.update_job(job_id, JobStatus.CANCELLED)
        await message.answer("Conversion cancelled.")
    except Exception as exc:
        logger.error("PDF tool %s failed: %s", tool, exc)
        await message.answer(f"❌ Operation failed: {exc}")
        await Repository.update_job(job_id, JobStatus.FAILED, error_message=str(exc))
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        await state.clear()
