from pathlib import Path
from PIL import Image, ImageOps
from app.config import settings
from app.utils.logger import logger


class ImageConversionError(Exception):
    pass


class ImageToPdfConverter:
    PAGE_SIZES = {
        "A4": (595.27, 841.89),
        "A5": (419.53, 595.27),
    }

    @classmethod
    def convert_images(
        cls,
        image_paths: list[Path],
        output_pdf_path: Path,
        page_size: str = "A4",
        orientation: str = "portrait",
        margin: int = 18,
    ) -> Path:
        if not image_paths:
            raise ImageConversionError("No input images provided.")

        processed_images: list[Image.Image] = []

        try:
            for path in image_paths:
                with Image.open(path) as img:
                    img = ImageOps.exif_transpose(img)

                    if img.width > settings.MAX_IMAGE_DIMENSION or img.height > settings.MAX_IMAGE_DIMENSION:
                        img.thumbnail(
                            (settings.MAX_IMAGE_DIMENSION, settings.MAX_IMAGE_DIMENSION),
                            Image.Resampling.LANCZOS,
                        )

                    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                        alpha = img.convert("RGBA")
                        bg = Image.new("RGBA", alpha.size, (255, 255, 255, 255))
                        bg.paste(alpha, mask=alpha.split()[3])
                        rgb_img = bg.convert("RGB")
                    else:
                        rgb_img = img.convert("RGB")

                    if page_size in cls.PAGE_SIZES:
                        target_width_pt, target_height_pt = cls.PAGE_SIZES[page_size]
                        if orientation == "landscape":
                            target_width_pt, target_height_pt = target_height_pt, target_width_pt

                        dpi = 150
                        target_w_px = int(target_width_pt * (dpi / 72))
                        target_h_px = int(target_height_pt * (dpi / 72))
                        margin_px = int(margin * (dpi / 72))

                        usable_w = max(100, target_w_px - (2 * margin_px))
                        usable_h = max(100, target_h_px - (2 * margin_px))

                        rgb_img.thumbnail((usable_w, usable_h), Image.Resampling.LANCZOS)

                        canvas = Image.new("RGB", (target_w_px, target_h_px), (255, 255, 255))
                        offset_x = (target_w_px - rgb_img.width) // 2
                        offset_y = (target_h_px - rgb_img.height) // 2
                        canvas.paste(rgb_img, (offset_x, offset_y))
                        processed_images.append(canvas)
                    else:
                        processed_images.append(rgb_img.copy())

            output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            first_image = processed_images[0]
            rest = processed_images[1:]

            first_image.save(
                output_pdf_path,
                format="PDF",
                save_all=True,
                append_images=rest,
                resolution=150.0,
                quality=85,
                optimize=True,
            )

            logger.info("Created PDF from %d image(s): %s", len(image_paths), output_pdf_path)
            return output_pdf_path

        except Exception as exc:
            logger.error("Failed to convert images to PDF: %s", exc)
            raise ImageConversionError(f"Image conversion failed: {exc}") from exc
        finally:
            for img in processed_images:
                img.close()
