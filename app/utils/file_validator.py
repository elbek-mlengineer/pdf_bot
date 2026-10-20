from pathlib import Path
from PIL import Image
from pypdf import PdfReader
from app.config import settings

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_DIMENSION * settings.MAX_IMAGE_DIMENSION


class FileValidationError(Exception):
    pass


class FileValidator:
    ALLOWED_IMAGE_MIMES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/tiff",
        "image/bmp",
    }

    ALLOWED_DOCUMENT_MIMES = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.oasis.opendocument.text",
        "application/rtf",
        "text/plain",
        "text/rtf",
        "text/csv",
        "text/html",
        "application/zip",
    }

    ALLOWED_DOCUMENT_EXTS = {
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".odt", ".txt", ".rtf", ".csv", ".html", ".htm",
    }

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        base = Path(filename).name
        clean = "".join(c for c in base if c.isalnum() or c in "._-")
        return clean or "uploaded_file"

    @staticmethod
    def detect_mime(file_path: Path) -> str:
        if HAS_MAGIC:
            m = magic.Magic(mime=True)
            return m.from_file(str(file_path))
        with open(file_path, "rb") as f:
            head = f.read(16)
        if head.startswith(b"%PDF-"):
            return "application/pdf"
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if head.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
            return "image/webp"
        if head.startswith(b"PK\x03\x04"):
            return "application/zip"
        return "application/octet-stream"

    @classmethod
    def validate_image(cls, file_path: Path, max_bytes: int) -> None:
        cls._check_size(file_path, max_bytes)
        mime = cls.detect_mime(file_path)
        if HAS_MAGIC and mime not in cls.ALLOWED_IMAGE_MIMES:
            raise FileValidationError(f"Unsupported image format ({mime}). Use JPG, PNG, or WEBP.")
        try:
            with Image.open(file_path) as img:
                img.verify()
                if img.width > settings.MAX_IMAGE_DIMENSION or img.height > settings.MAX_IMAGE_DIMENSION:
                    raise FileValidationError(
                        f"Image dimensions ({img.width}x{img.height}) exceed safety limit."
                    )
        except FileValidationError:
            raise
        except Exception as exc:
            raise FileValidationError("Corrupted or invalid image file.") from exc

    @classmethod
    def validate_document(cls, file_path: Path, max_bytes: int) -> None:
        cls._check_size(file_path, max_bytes)
        ext = file_path.suffix.lower()
        if ext not in cls.ALLOWED_DOCUMENT_EXTS:
            raise FileValidationError(f"Unsupported file extension '{ext}'.")
        mime = cls.detect_mime(file_path)
        if HAS_MAGIC and mime not in cls.ALLOWED_DOCUMENT_MIMES:
            raise FileValidationError(f"File content ({mime}) does not match supported Office formats.")

    @classmethod
    def validate_pdf(cls, file_path: Path, max_bytes: int) -> int:
        cls._check_size(file_path, max_bytes)
        with open(file_path, "rb") as f:
            if not f.read(5).startswith(b"%PDF-"):
                raise FileValidationError("File is not a valid PDF document.")
        try:
            reader = PdfReader(str(file_path))
            if reader.is_encrypted:
                raise FileValidationError("Password-protected PDFs cannot be processed.")
            num_pages = len(reader.pages)
            if num_pages == 0:
                raise FileValidationError("PDF has 0 pages.")
            if num_pages > settings.MAX_PDF_PAGES:
                raise FileValidationError(
                    f"PDF has {num_pages} pages, exceeding the limit of {settings.MAX_PDF_PAGES}."
                )
            return num_pages
        except FileValidationError:
            raise
        except Exception as exc:
            raise FileValidationError("Corrupted or unreadable PDF file.") from exc

    @staticmethod
    def _check_size(file_path: Path, max_bytes: int) -> None:
        if not file_path.exists():
            raise FileValidationError("File does not exist.")
        size = file_path.stat().st_size
        if size == 0:
            raise FileValidationError("Uploaded file is empty (0 bytes).")
        if size > max_bytes:
            raise FileValidationError(
                f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB."
            )
