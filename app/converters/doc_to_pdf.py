import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from app.config import settings
from app.utils.file_validator import FileValidator
from app.utils.logger import logger


class DocumentConversionError(Exception):
    pass


class DocumentToPdfConverter:
    @staticmethod
    async def convert(input_path: Path, output_dir: Path) -> Path:
        if not input_path.exists():
            raise DocumentConversionError(f"Input file not found: {input_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        expected_pdf = output_dir / f"{input_path.stem}.pdf"
        job_profile_dir = Path(tempfile.mkdtemp(prefix="lo_profile_"))

        cmd = [
            "libreoffice",
            "--headless",
            "--invisible",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            f"-env:UserInstallation=file://{job_profile_dir.resolve()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir.resolve()),
            str(input_path.resolve()),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=dict(os.environ, HOME=str(job_profile_dir)),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=settings.CONVERSION_TIMEOUT_SECONDS,
                )
            except TimeoutError as exc:
                process.kill()
                await process.communicate()
                raise DocumentConversionError(
                    f"Conversion timed out after {settings.CONVERSION_TIMEOUT_SECONDS}s."
                ) from exc

            if process.returncode != 0:
                err_str = stderr.decode(errors="replace")
                logger.error("LibreOffice error: %s", err_str)
                raise DocumentConversionError("LibreOffice failed to convert document.")

            if not expected_pdf.exists() or expected_pdf.stat().st_size == 0:
                raise DocumentConversionError("Output PDF was not generated.")

            FileValidator.validate_pdf(expected_pdf, settings.max_file_size_bytes * 2)
            return expected_pdf

        finally:
            shutil.rmtree(job_profile_dir, ignore_errors=True)
