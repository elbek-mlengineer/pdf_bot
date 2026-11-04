from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.commands import set_private_commands
from app.i18n import LANGUAGES, current_language, labels, tr
from app.keyboards.language import language_keyboard
from app.keyboards.main_menu import get_main_menu
from app.middlewares.language import language_key
from app.utils.session_files import clear_session

router = Router(name="common_router")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await clear_session(state)
    user = message.from_user
    if message.chat.type == "private":
        await set_private_commands(message.bot, message.chat.id, current_language.get())

    text = tr("welcome", escape(user.first_name) if user else "👋")
    await message.answer(text, reply_markup=get_main_menu())
    await choose_language(message)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await clear_session(state)
    await message.answer(tr("cancel_clean"), reply_markup=get_main_menu())


@router.callback_query(F.data == "action:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await clear_session(state)
    await callback.message.edit_text(tr("cancel_done"))
    await callback.answer()


@router.message(Command("help"))
@router.message(F.text.in_(labels("menu_help")))
async def cmd_help(message: Message):
    contact = InlineKeyboardButton(text=tr("contact_admin"), url="https://t.me/Heart_07_07")
    await message.answer(tr("help"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[contact]]))


@router.message(Command("language", "lang"))
@router.message(F.text.in_(labels("language")))
async def choose_language(message: Message):
    await message.answer(tr("choose_language"), reply_markup=language_keyboard())


@router.callback_query(F.data.in_({f"lang:{code}" for code in LANGUAGES}))
async def select_language(callback: CallbackQuery, state: FSMContext):
    code = callback.data.split(":", 1)[1]
    await state.storage.set_data(
        language_key(callback.bot.id, callback.from_user.id), {"language": code}
    )
    current_language.set(code)
    await callback.answer()
    if callback.message.chat.type == "private":
        await set_private_commands(callback.bot, callback.message.chat.id, code)
    await callback.message.edit_text(tr("language_saved"))
    await callback.message.answer(
        tr("welcome", escape(callback.from_user.first_name)), reply_markup=get_main_menu()
    )
