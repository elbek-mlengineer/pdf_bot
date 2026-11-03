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
from app.i18n import labels, layout_name, tr
from app.keyboards.inline import get_image_options_keyboard
from app.queue.cancellation import ConversionCancelled, cancellation_scope
from app.queue.local import run_local
from app.utils.file_validator import FileValidationError, FileValidator
from app.utils.logger import logger
from app.utils.session_files import clear_session

router = Router(name="images_router")


class ImageFlow(StatesGroup):
    collecting_images = State()


@router.message(F.text.in_(labels("menu_images")))
async def start_image_to_pdf(message: Message, state: FSMContext):
    await clear_session(state)
    job_id = str(uuid.uuid4())
    job_dir = settings.TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    prefs = await Repository.get_user_settings(message.from_user.id)
    await state.update_data(
        job_id=job_id,
        job_dir=str(job_dir),
        files=[],
        default_size=prefs.page_size,
        default_orient=prefs.orientation,
    )
    await state.set_state(ImageFlow.collecting_images)

    await message.answer(
        tr("image_prompt"),
        reply_markup=get_image_options_keyboard(prefs.page_size, prefs.orientation),
    )


@router.message(ImageFlow.collecting_images, F.photo)
async def handle_image_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await _save_and_validate_image(message, state, photo.file_id, photo.file_size or 0, ".jpg")


@router.message(ImageFlow.collecting_images, F.document)
async def handle_image_document(message: Message, state: FSMContext):
    doc: Document = message.document
    ext = Path(doc.file_name or "img.jpg").suffix.lower() or ".jpg"
    await _save_and_validate_image(message, state, doc.file_id, doc.file_size or 0, ext)


async def _save_and_validate_image(
    message: Message, state: FSMContext, file_id: str, file_size: int, ext: str
):
    data = await state.get_data()
    file_list: list[str] = data.get("files", [])

    if len(file_list) >= settings.MAX_IMAGE_COUNT:
        await message.answer(tr("images_max", settings.MAX_IMAGE_COUNT))
        return

    if file_size > settings.max_file_size_bytes:
        await message.answer(tr("size_limit", settings.MAX_FILE_SIZE_MB))
        return

    job_dir = Path(data["job_dir"])
    file_path = job_dir / f"img_{len(file_list):03d}{ext}"
    await bot.download(file_id, destination=file_path)

    try:
        FileValidator.validate_image(file_path, settings.max_file_size_bytes)
        file_list.append(str(file_path))
        await state.update_data(files=file_list)
        await message.answer(
            tr("image_added", len(file_list)),
            reply_markup=get_image_options_keyboard(
                data.get("default_size", "A4"), data.get("default_orient", "portrait")
            ),
        )
    except FileValidationError as e:
        file_path.unlink(missing_ok=True)
        await message.answer(tr("rejected", e))


@router.callback_query(ImageFlow.collecting_images, F.data.startswith("img_opt:"))
async def process_image_conversion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    file_list: list[str] = data.get("files", [])
    job_id = data.get("job_id")
    job_dir = Path(data.get("job_dir"))

    if not file_list:
        await callback.answer(tr("need_image"), show_alert=True)
        return

    active_count = await Repository.count_active_user_jobs(callback.from_user.id)
    if active_count >= settings.MAX_CONCURRENT_JOBS_PER_USER:
        await callback.answer(tr("wait_jobs"), show_alert=True)
        return

    _, page_size, orientation = callback.data.split(":")
    await callback.message.edit_text(tr("image_work"))

    output_pdf = job_dir / "converted_images.pdf"
    start_ts = time.perf_counter()
    await Repository.create_job(job_id, callback.from_user.id, JobType.IMAGES_TO_PDF.value)

    try:
        await Repository.update_job(job_id, JobStatus.PROCESSING)

        with cancellation_scope(state.key) as signal:
            await run_local(
                "images", [file_list, str(output_pdf), page_size, orientation, 18], signal
            )

        elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
        input_file = FSInputFile(str(output_pdf), filename="Images_Converted.pdf")
        await callback.message.answer_document(
            document=input_file,
            caption=tr(
                "images_done",
                len(file_list),
                layout_name(page_size),
                layout_name(orientation.title()),
                elapsed_ms,
            ),
        )
        await Repository.update_job(job_id, JobStatus.COMPLETED, execution_time_ms=elapsed_ms)

    except ConversionCancelled:
        await Repository.update_job(job_id, JobStatus.CANCELLED)
        await callback.message.answer(tr("cancelled"))
    except Exception as exc:
        logger.error("Image to PDF failed: %s", exc)
        await callback.message.answer(tr("image_error", exc))
        await Repository.update_job(job_id, JobStatus.FAILED, error_message=str(exc))
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        await state.clear()
        await callback.answer()
