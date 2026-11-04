from pathlib import Path
from tempfile import TemporaryDirectory

from aiohttp import ClientConnectionError
from aiogram import F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, Message

from app.config import settings
from app.handlers.filename import name_input, validate_filename
from app.i18n import labels, tr
from app.utils.logger import logger
from app.utils.session_files import clear_session

router = Router(name="rename")
TRANSFER_TIMEOUT = 300
CLOUD_DOWNLOAD_LIMIT_MB = 20


class RenameFlow(StatesGroup):
    waiting_for_file = State()
    waiting_for_name = State()


@router.message(Command("rename"))
@router.message(F.text.in_(labels("menu_rename")))
async def start_rename(message: Message, state: FSMContext):
    await clear_session(state)
    await state.set_state(RenameFlow.waiting_for_file)
    await message.answer(tr("rename_upload"))


@router.message(
    StateFilter(None, RenameFlow.waiting_for_file, RenameFlow.waiting_for_name), F.document
)
async def receive_file(message: Message, state: FSMContext):
    document = message.document
    limit_mb = settings.MAX_FILE_SIZE_MB
    if not message.bot.session.api.is_local:
        limit_mb = min(limit_mb, CLOUD_DOWNLOAD_LIMIT_MB)
    if (document.file_size or 0) > limit_mb * 1024 * 1024:
        await message.answer(tr("size_limit", limit_mb))
        return
    await state.update_data(rename_file_id=document.file_id, original_name=document.file_name or "")
    await state.set_state(RenameFlow.waiting_for_name)
    await message.answer(tr("rename_name"))


@router.message(RenameFlow.waiting_for_name, name_input)
async def send_renamed_file(message: Message, state: FSMContext):
    data = await state.get_data()
    name = validate_filename(message.text.strip())
    if name and not Path(name).suffix:
        name = validate_filename(name + Path(data["original_name"]).suffix)
    if not name:
        await message.answer(tr("invalid_pdf_name"))
        return

    try:
        with TemporaryDirectory(dir=settings.TEMP_DIR) as folder:
            payload = Path(folder) / "payload"
            for attempt in range(2):
                try:
                    await message.bot.download(
                        data["rename_file_id"], destination=payload, timeout=TRANSFER_TIMEOUT
                    )
                    break
                except (TimeoutError, ClientConnectionError, TelegramNetworkError):
                    if attempt:
                        raise
                    payload.unlink(missing_ok=True)
            upload = message.answer_document(
                document=FSInputFile(payload, filename=name), disable_content_type_detection=True
            )
            await message.bot(upload, request_timeout=TRANSFER_TIMEOUT)
    except Exception:
        logger.exception("File rename transfer failed")
        await message.answer(tr("rename_error"))
        return
    await state.clear()
