from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_image_options_keyboard(default_size: str = "A4", default_orient: str = "portrait") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⚡ Create PDF ({default_size} {default_orient.title()})",
                    callback_data=f"img_opt:{default_size}:{default_orient}",
                )
            ],
            [
                InlineKeyboardButton(text="📄 A4 Portrait", callback_data="img_opt:A4:portrait"),
                InlineKeyboardButton(text="📄 A4 Landscape", callback_data="img_opt:A4:landscape"),
            ],
            [
                InlineKeyboardButton(text="📑 A5 Portrait", callback_data="img_opt:A5:portrait"),
                InlineKeyboardButton(text="📑 A5 Landscape", callback_data="img_opt:A5:landscape"),
            ],
            [
                InlineKeyboardButton(text="🖼 Original Size", callback_data="img_opt:ORIGINAL:portrait"),
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="action:cancel"),
            ],
        ]
    )


def get_merge_action_keyboard(count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🚀 Merge {count} Files into PDF", callback_data="merge:execute"
                ),
            ],
            [
                InlineKeyboardButton(text="❌ Clear & Cancel", callback_data="action:cancel"),
            ],
        ]
    )


def get_pdf_tools_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗜 Compress PDF", callback_data="tool:compress"),
                InlineKeyboardButton(text="🔢 Add Page Numbers", callback_data="tool:page_numbers"),
            ],
            [
                InlineKeyboardButton(text="🔄 Rotate 90°", callback_data="tool:rotate:90"),
                InlineKeyboardButton(text="🔄 Rotate 180°", callback_data="tool:rotate:180"),
            ],
            [
                InlineKeyboardButton(text="✂️ Extract Pages", callback_data="tool:extract_pages"),
                InlineKeyboardButton(text="📑 Split All Pages (ZIP)", callback_data="tool:split"),
            ],
            [
                InlineKeyboardButton(text="🖼 Extract Images (ZIP)", callback_data="tool:extract_images"),
                InlineKeyboardButton(text="🏷 Edit Metadata", callback_data="tool:metadata"),
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="action:cancel"),
            ],
        ]
    )


def get_settings_keyboard(page_size: str, orientation: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅ ' if page_size == 'A4' else ''}A4",
                    callback_data="set_size:A4",
                ),
                InlineKeyboardButton(
                    text=f"{'✅ ' if page_size == 'A5' else ''}A5",
                    callback_data="set_size:A5",
                ),
                InlineKeyboardButton(
                    text=f"{'✅ ' if page_size == 'ORIGINAL' else ''}Original",
                    callback_data="set_size:ORIGINAL",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{'✅ ' if orientation == 'portrait' else ''}Portrait",
                    callback_data="set_orient:portrait",
                ),
                InlineKeyboardButton(
                    text=f"{'✅ ' if orientation == 'landscape' else ''}Landscape",
                    callback_data="set_orient:landscape",
                ),
            ],
        ]
    )
