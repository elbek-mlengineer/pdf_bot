import shutil
import time
import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, Message

from app.config import settings
from app.database.models import JobStatus, JobType
from app.database.repositories import Repository
from app.handlers.filename import ask_before_upload
from app.i18n import MENU_LABELS, labels, tr
from app.queue.cancellation import ConversionCancelled, cancellation_scope
from app.queue.local import run_local
from app.utils.logger import logger
from app.utils.session_files import clear_session

router = Router(name="text_router")


class TextFlow(StatesGroup):
    waiting_for_text = State()


@router.message(F.text.in_(labels("menu_text")))
async def start_text_to_pdf(message: Message, state: FSMContext):
    await clear_session(state)
    await ask_before_upload(message, state, TextFlow.waiting_for_text, "text_prompt")


@router.message(TextFlow.waiting_for_text, F.text, ~F.text.in_(MENU_LABELS))
async def process_text_message(message: Message, state: FSMContext):
    text_content = message.text.strip()
    if not text_content:
        await message.answer(tr("text_empty"))
        return

    job_id = str(uuid.uuid4())
    job_dir = settings.TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = job_dir / "text_document.pdf"

    status_msg = await message.answer(tr("text_work"))
    start_ts = time.perf_counter()
    await Repository.create_job(job_id, message.from_user.id, JobType.TEXT_TO_PDF.value)

    try:
        await Repository.update_job(job_id, JobStatus.PROCESSING)

        with cancellation_scope(state.key) as signal:
            await run_local("text", [text_content, str(out_pdf), "Document"], signal)

        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        input_file = FSInputFile(
            str(out_pdf), filename=(await state.get_data()).get("pdf_name", "Text_Document.pdf")
        )
        await status_msg.delete()
        await message.answer_document(
            document=input_file,
            caption=tr("text_done", elapsed_ms),
        )
        await Repository.update_job(job_id, JobStatus.COMPLETED, execution_time_ms=elapsed_ms)

    except ConversionCancelled:
        await Repository.update_job(job_id, JobStatus.CANCELLED)
        await message.answer(tr("cancelled"))
    except Exception as exc:
        logger.error("Text to PDF error: %s", exc)
        await message.answer(tr("text_error", exc))
        await Repository.update_job(job_id, JobStatus.FAILED, error_message=str(exc))
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        await state.clear()
