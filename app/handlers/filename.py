import re
import unicodedata

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.i18n import MENU_LABELS, tr

router = Router(name="pdf_filename")
name_input = F.text & ~F.text.in_(MENU_LABELS) & ~F.text.startswith("/")


class FilenameFlow(StatesGroup):
    waiting = State()


def pdf_filename(text: str) -> str | None:
    stem = text.strip()
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4].rstrip()
    if not stem or stem in {".", ".."} or stem.endswith("."):
        return None
    if re.search(r'[<>:"/\\|?*]', stem) or any(unicodedata.category(c) == "Cc" for c in stem):
        return None
    name = stem + ".pdf"
    return name if len(name.encode("utf-8")) <= 255 else None


async def read_filename(message: Message) -> str | None:
    name = pdf_filename(message.text)
    if not name:
        await message.answer(tr("invalid_pdf_name"))
    return name


async def ask_before_upload(message, state, next_state, prompt, *args):
    await state.update_data(next_state=next_state.state, upload_prompt=prompt, prompt_args=args)
    await state.set_state(FilenameFlow.waiting)
    await message.answer(tr("ask_pdf_name"))


@router.message(FilenameFlow.waiting, name_input)
async def accept_filename(message: Message, state: FSMContext):
    name = await read_filename(message)
    if name:
        data = await state.update_data(pdf_name=name)
        await state.set_state(data["next_state"])
        await message.answer(tr(data["upload_prompt"], *data["prompt_args"]))
