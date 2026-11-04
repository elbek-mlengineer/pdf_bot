"""Exercise the production Office sandbox with a synthetic job."""
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import settings
from app.queue.tasks import run_doc_to_pdf_job


def main():
    with TemporaryDirectory(dir=settings.TEMP_DIR) as folder:
        source = Path(folder) / "sample.txt"
        source.write_text("PDF bot deployment check", encoding="utf-8")
        result = Path(run_doc_to_pdf_job(str(source), str(source.parent / "converted")))
        if not result.read_bytes().startswith(b"%PDF-"):
            raise RuntimeError("Conversion did not produce a PDF")


if __name__ == "__main__":
    main()
