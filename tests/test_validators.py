import pytest
from app.utils.file_validator import FileValidationError, FileValidator


def test_reject_empty_file(temp_dir):
    empty = temp_dir / "empty.pdf"
    empty.touch()
    with pytest.raises(FileValidationError):
        FileValidator.validate_pdf(empty, max_bytes=1024 * 1024)


def test_reject_oversized_file(temp_dir):
    big = temp_dir / "big.pdf"
    big.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    with pytest.raises(FileValidationError):
        FileValidator.validate_pdf(big, max_bytes=512)


def test_reject_fake_pdf_extension(temp_dir):
    fake = temp_dir / "malicious.pdf"
    fake.write_bytes(b"This is plain text pretending to be a PDF")
    with pytest.raises(FileValidationError):
        FileValidator.validate_pdf(fake, max_bytes=1024 * 1024)


def test_sanitize_filename_prevents_path_traversal():
    dirty = "../../etc/passwd"
    clean = FileValidator.sanitize_filename(dirty)
    assert clean == "passwd"
    assert "/" not in clean
    assert ".." not in clean
