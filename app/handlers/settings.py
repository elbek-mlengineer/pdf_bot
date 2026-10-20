from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from app.database.repositories import Repository
from app.keyboards.inline import get_settings_keyboard

router = Router(name="settings_router")


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Settings")
async def cmd_settings(message: Message):
    prefs = await Repository.get_user_settings(message.from_user.id)
    await message.answer(
        "⚙️ <b>Conversion Preferences</b>\n\n"
        f"• Default Page Size: <b>{prefs.page_size}</b>\n"
        f"• Default Orientation: <b>{prefs.orientation.title()}</b>\n\n"
        "Tap below to update your defaults:",
        reply_markup=get_settings_keyboard(prefs.page_size, prefs.orientation),
    )


@router.callback_query(F.data.startswith("set_size:"))
async def cb_set_size(callback: CallbackQuery):
    size = callback.data.split(":")[1]
    prefs = await Repository.update_user_settings(callback.from_user.id, page_size=size)
    await callback.message.edit_text(
        "⚙️ <b>Conversion Preferences</b>\n\n"
        f"• Default Page Size: <b>{prefs.page_size}</b>\n"
        f"• Default Orientation: <b>{prefs.orientation.title()}</b>\n\n"
        "Tap below to update your defaults:",
        reply_markup=get_settings_keyboard(prefs.page_size, prefs.orientation),
    )
    await callback.answer(f"Page size set to {size}")


@router.callback_query(F.data.startswith("set_orient:"))
async def cb_set_orient(callback: CallbackQuery):
    orient = callback.data.split(":")[1]
    prefs = await Repository.update_user_settings(callback.from_user.id, orientation=orient)
    await callback.message.edit_text(
        "⚙️ <b>Conversion Preferences</b>\n\n"
        f"• Default Page Size: <b>{prefs.page_size}</b>\n"
        f"• Default Orientation: <b>{prefs.orientation.title()}</b>\n\n"
        "Tap below to update your defaults:",
        reply_markup=get_settings_keyboard(prefs.page_size, prefs.orientation),
    )
    await callback.answer(f"Orientation set to {orient.title()}")
