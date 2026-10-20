import io
import zipfile
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from app.utils.logger import logger


class PdfToolsError(Exception):
    pass


class PdfTools:
    @classmethod
    def merge_pdfs(cls, pdf_paths: list[Path], output_path: Path) -> Path:
        if len(pdf_paths) < 2:
            raise PdfToolsError("At least two PDF files are required for merging.")

        writer = PdfWriter()
        try:
            for path in pdf_paths:
                reader = PdfReader(str(path))
                if reader.is_encrypted:
                    raise PdfToolsError(f"File '{path.name}' is password-protected.")
                for page in reader.pages:
                    writer.add_page(page)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            return output_path
        except PdfToolsError:
            raise
        except Exception as exc:
            logger.error("Failed to merge PDFs: %s", exc)
            raise PdfToolsError(f"PDF merging failed: {exc}") from exc
        finally:
            writer.close()

    @classmethod
    def compress_pdf(cls, input_path: Path, output_path: Path) -> Path:
        writer = PdfWriter()
        try:
            reader = PdfReader(str(input_path))
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            return output_path
        except Exception as exc:
            raise PdfToolsError(f"Failed to compress PDF: {exc}") from exc
        finally:
            writer.close()

    @classmethod
    def rotate_pdf(cls, input_path: Path, output_path: Path, angle: int = 90) -> Path:
        if angle not in (90, 180, 270):
            raise PdfToolsError("Rotation angle must be 90, 180, or 270 degrees.")
        writer = PdfWriter()
        try:
            reader = PdfReader(str(input_path))
            for page in reader.pages:
                page.rotate(angle)
                writer.add_page(page)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            return output_path
        except Exception as exc:
            raise PdfToolsError(f"Failed to rotate PDF: {exc}") from exc
        finally:
            writer.close()

    @classmethod
    def extract_pages(cls, input_path: Path, output_path: Path, page_spec: str) -> Path:
        writer = PdfWriter()
        try:
            reader = PdfReader(str(input_path))
            total = len(reader.pages)
            selected_indices = cls._parse_page_spec(page_spec, total)
            if not selected_indices:
                raise PdfToolsError("No valid pages matched your selection.")

            for idx in selected_indices:
                writer.add_page(reader.pages[idx])

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            return output_path
        except PdfToolsError:
            raise
        except Exception as exc:
            raise PdfToolsError(f"Page extraction failed: {exc}") from exc
        finally:
            writer.close()

    @classmethod
    def split_pdf_to_zip(cls, input_path: Path, output_zip_path: Path) -> Path:
        try:
            reader = PdfReader(str(input_path))
            output_zip_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for idx, page in enumerate(reader.pages, start=1):
                    writer = PdfWriter()
                    writer.add_page(page)
                    buf = io.BytesIO()
                    writer.write(buf)
                    zf.writestr(f"page_{idx:03d}.pdf", buf.getvalue())
                    writer.close()
            return output_zip_path
        except Exception as exc:
            raise PdfToolsError(f"Failed to split PDF: {exc}") from exc

    @classmethod
    def add_page_numbers(cls, input_path: Path, output_path: Path) -> Path:
        writer = PdfWriter()
        try:
            reader = PdfReader(str(input_path))
            total = len(reader.pages)
            for idx, page in enumerate(reader.pages, start=1):
                w = float(page.mediabox.width)
                h = float(page.mediabox.height)
                packet = io.BytesIO()
                c = canvas.Canvas(packet, pagesize=(w, h))
                c.setFont("Helvetica", 9)
                c.setFillColorRGB(0.3, 0.3, 0.3)
                c.drawRightString(w - 36, 24, f"{idx} / {total}")
                c.save()
                packet.seek(0)
                overlay = PdfReader(packet).pages[0]
                page.merge_page(overlay)
                writer.add_page(page)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            return output_path
        except Exception as exc:
            raise PdfToolsError(f"Failed to add page numbers: {exc}") from exc
        finally:
            writer.close()

    @classmethod
    def extract_images_to_zip(cls, input_path: Path, output_zip_path: Path) -> Path:
        try:
            reader = PdfReader(str(input_path))
            img_count = 0
            output_zip_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p_idx, page in enumerate(reader.pages, start=1):
                    for img_file in page.images:
                        img_count += 1
                        zf.writestr(f"page{p_idx}_{img_count}_{img_file.name}", img_file.data)
            if img_count == 0:
                raise PdfToolsError("No embedded images were found inside this PDF.")
            return output_zip_path
        except PdfToolsError:
            raise
        except Exception as exc:
            raise PdfToolsError(f"Image extraction failed: {exc}") from exc

    @classmethod
    def update_metadata(
        cls, input_path: Path, output_path: Path, title: str, author: str
    ) -> Path:
        writer = PdfWriter()
        try:
            reader = PdfReader(str(input_path))
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata(
                {
                    "/Title": title,
                    "/Author": author,
                    "/Producer": "Telegram PDF Converter Bot",
                }
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            return output_path
        except Exception as exc:
            raise PdfToolsError(f"Metadata update failed: {exc}") from exc
        finally:
            writer.close()

    @staticmethod
    def _parse_page_spec(spec: str, max_pages: int) -> list[int]:
        indices: list[int] = []
        parts = [p.strip() for p in spec.split(",") if p.strip()]
        for part in parts:
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                start, end = int(start_s), int(end_s)
                if start > end or start < 1 or end > max_pages:
                    raise PdfToolsError(f"Invalid page range '{part}' (document has {max_pages} pages).")
                for p in range(start, end + 1):
                    if (p - 1) not in indices:
                        indices.append(p - 1)
            else:
                p = int(part)
                if p < 1 or p > max_pages:
                    raise PdfToolsError(f"Page {p} is out of bounds (1-{max_pages}).")
                if (p - 1) not in indices:
                    indices.append(p - 1)
        return indices
