from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.i18n import layout_name, tr


def get_image_options_keyboard(
    default_size: str = "A4", default_orient: str = "portrait"
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=tr(
                        "create_pdf", layout_name(default_size), layout_name(default_orient.title())
                    ),
                    callback_data=f"img_opt:{default_size}:{default_orient}",
                )
            ],
            [
                InlineKeyboardButton(text=tr("a4_portrait"), callback_data="img_opt:A4:portrait"),
                InlineKeyboardButton(text=tr("a4_landscape"), callback_data="img_opt:A4:landscape"),
            ],
            [
                InlineKeyboardButton(text=tr("a5_portrait"), callback_data="img_opt:A5:portrait"),
                InlineKeyboardButton(text=tr("a5_landscape"), callback_data="img_opt:A5:landscape"),
            ],
            [
                InlineKeyboardButton(
                    text=tr("original_size"), callback_data="img_opt:ORIGINAL:portrait"
                ),
            ],
            [
                InlineKeyboardButton(text=tr("cancel_button"), callback_data="action:cancel"),
            ],
        ]
    )


def get_merge_action_keyboard(count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=tr("merge_button", count), callback_data="merge:execute"),
            ],
            [
                InlineKeyboardButton(text=tr("clear_button"), callback_data="action:cancel"),
            ],
        ]
    )


def get_pdf_tools_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=tr("compress"), callback_data="tool:compress"),
                InlineKeyboardButton(text=tr("page_numbers"), callback_data="tool:page_numbers"),
            ],
            [
                InlineKeyboardButton(text=tr("rotate90"), callback_data="tool:rotate:90"),
                InlineKeyboardButton(text=tr("rotate180"), callback_data="tool:rotate:180"),
            ],
            [
                InlineKeyboardButton(text=tr("extract_pages"), callback_data="tool:extract_pages"),
                InlineKeyboardButton(text=tr("split"), callback_data="tool:split"),
            ],
            [
                InlineKeyboardButton(
                    text=tr("extract_images"), callback_data="tool:extract_images"
                ),
                InlineKeyboardButton(text=tr("metadata"), callback_data="tool:metadata"),
            ],
            [
                InlineKeyboardButton(text=tr("cancel_button"), callback_data="action:cancel"),
            ],
        ]
    )


def get_settings_keyboard(page_size: str, orientation: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=tr("a4", "✅ " if page_size == "A4" else ""),
                    callback_data="set_size:A4",
                ),
                InlineKeyboardButton(
                    text=tr("a5", "✅ " if page_size == "A5" else ""),
                    callback_data="set_size:A5",
                ),
                InlineKeyboardButton(
                    text=tr("original", "✅ " if page_size == "ORIGINAL" else ""),
                    callback_data="set_size:ORIGINAL",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr("portrait", "✅ " if orientation == "portrait" else ""),
                    callback_data="set_orient:portrait",
                ),
                InlineKeyboardButton(
                    text=tr("landscape", "✅ " if orientation == "landscape" else ""),
                    callback_data="set_orient:landscape",
                ),
            ],
        ]
    )
