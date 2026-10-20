import shutil
from pathlib import Path
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from app.database.repositories import Repository
from app.keyboards.main_menu import get_main_menu

router = Router(name="common_router")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await _cleanup_state(state)
    user = message.from_user
    if user:
        await Repository.upsert_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

    text = (
        f"👋 Hello, <b>{user.first_name if user else 'User'}</b>!\n\n"
        "Welcome to the <b>Professional PDF Converter Bot</b>.\n\n"
        "Select an operation from the menu below:\n"
        "• 🖼 <b>Images to PDF</b>: Combine JPG, PNG, WEBP photos\n"
        "• 📝 <b>Text to PDF</b>: Multi-page Unicode (Uzbek Latin/Cyrillic, RU, EN)\n"
        "• 📄 <b>Convert Document</b>: DOCX, XLSX, PPTX, ODT, RTF, CSV, HTML\n"
        "• 📚 <b>Merge PDF Files</b>: Combine PDFs & Office documents\n"
        "• 🛠 <b>PDF Tools</b>: Compress, Rotate, Split, Extract Pages/Images, Page Numbers\n"
        "• ⚙️ <b>Settings</b>: Configure default page size and orientation\n\n"
        "Use /cancel at any time to stop the current action."
    )
    await message.answer(text, reply_markup=get_main_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await _cleanup_state(state)
    await message.answer("❌ Current operation cancelled and temporary files removed.", reply_markup=get_main_menu())


@router.callback_query(F.data == "action:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await _cleanup_state(state)
    await callback.message.edit_text("❌ Operation cancelled.")
    await callback.answer()


@router.message(Command("help"))
@router.message(F.text == "❓ Help")
async def cmd_help(message: Message):
    text = (
        "📖 <b>Bot User Guide</b>\n\n"
        "1. <b>Images to PDF</b>: Upload up to 50 images, then choose A4, A5, or Original layout.\n"
        "2. <b>Text to PDF</b>: Send any text message (supports o‘, g‘, ў, қ, ғ, ҳ). Use <code># Heading</code> for titles.\n"
        "3. <b>Convert Document to PDF</b>: Upload DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, RTF, TXT, CSV, or HTML.\n"
        "4. <b>Merge PDF Files</b>: Send multiple PDFs in order and tap 'Merge'.\n"
        "5. <b>PDF Tools</b>: Upload a single PDF to compress, rotate, extract pages, split, or add page numbers.\n\n"
        "🔒 <b>Privacy & Security</b>: All uploaded and converted files are automatically deleted immediately after processing."
    )
    await message.answer(text)


async def _cleanup_state(state: FSMContext) -> None:
    data = await state.get_data()
    job_dir = data.get("job_dir")
    if job_dir:
        shutil.rmtree(Path(job_dir), ignore_errors=True)
    await state.clear()
