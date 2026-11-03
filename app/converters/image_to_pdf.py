from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


class ImageConversionError(Exception):
    pass


class ImageToPdfConverter:
    PAGE_SIZES = {"A4": (595.27, 841.89), "A5": (419.53, 595.27)}

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

        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf = Canvas(str(output_pdf_path), pageCompression=1)
        try:
            for path in image_paths:
                with Image.open(path) as source:
                    # Pass JPEG bytes directly when no EXIF transform is needed.
                    # Otherwise embed the oriented pixels with lossless compression.
                    with ImageOps.exif_transpose(source) as img:
                        width, height = img.size
                        if page_size in cls.PAGE_SIZES:
                            pw, ph = cls.PAGE_SIZES[page_size]
                            if orientation == "landscape":
                                pw, ph = ph, pw
                            scale = min((pw - 2 * margin) / width, (ph - 2 * margin) / height)
                        else:
                            scale = 72 / 150
                            pw, ph = width * scale, height * scale
                        pdf.setPageSize((pw, ph))
                        direct = source.format == "JPEG" and source.getexif().get(274, 1) == 1
                        if direct:
                            image = ImageReader(str(path))
                        else:
                            mode = "RGBA" if img.has_transparency_data else "RGB"
                            image = ImageReader(img.convert(mode))
                        w, h = width * scale, height * scale
                        pdf.drawImage(image, (pw - w) / 2, (ph - h) / 2, w, h, mask="auto")
                        pdf.showPage()
            pdf.save()
        except Exception as exc:
            raise ImageConversionError(f"Image conversion failed: {exc}") from exc
        return output_pdf_path
