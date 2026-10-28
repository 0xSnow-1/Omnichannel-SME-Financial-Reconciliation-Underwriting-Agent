import os

import pytest
from sme_copilot.services.file_storage import (
    MAX_FILE_SIZE,
    MAX_FILES,
    cleanup_files,
    validate_file,
)

# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------


def test_validate_pdf_ok():
    assert validate_file("statement.pdf", "application/pdf", 1024) is None


def test_validate_csv_ok():
    assert validate_file("export.csv", "text/csv", 512) is None


def test_validate_xlsx_ok():
    assert (
        validate_file(
            "sales.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            2048,
        )
        is None
    )


def test_validate_png_ok():
    assert validate_file("receipt.png", "image/png", 4096) is None


def test_validate_jpeg_ok():
    assert validate_file("receipt.jpg", "image/jpeg", 4096) is None


def test_validate_unsupported_type():
    err = validate_file("malware.exe", "application/x-msdownload", 100)
    assert err is not None
    assert "exe" in err.lower() or "Unsupported" in err


def test_validate_oversized():
    err = validate_file("big.pdf", "application/pdf", MAX_FILE_SIZE + 1)
    assert err is not None
    assert "25 MB" in err


def test_validate_exactly_at_limit():
    # Exactly at the limit should pass
    assert validate_file("edge.pdf", "application/pdf", MAX_FILE_SIZE) is None


def test_validate_zero_bytes():
    # Zero-byte file with valid type should pass (no size rule against it)
    assert validate_file("empty.pdf", "application/pdf", 0) is None


# ---------------------------------------------------------------------------
# save_file
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def temp_upload_dir(monkeypatch, tmp_path):
    """Redirect all file saves to a temp directory during tests."""
    import sme_copilot.services.file_storage as fs_module

    original = fs_module.UPLOAD_DIR
    fs_module.UPLOAD_DIR = tmp_path / "uploads"
    yield
    fs_module.UPLOAD_DIR = original


def test_save_file_creates_fileref():
    from sme_copilot.services.file_storage import save_file as sf

    ref = sf("app-123", "statement.pdf", "application/pdf", b"%PDF fake data")
    assert ref.filename == "statement.pdf"
    assert ref.content_type == "application/pdf"
    assert ref.size_bytes == len(b"%PDF fake data")
    assert "statement.pdf" in ref.storage_path
    assert os.path.exists(ref.storage_path)


def test_save_file_uuid_prefix():
    import re

    from sme_copilot.services.file_storage import save_file as sf

    ref = sf("app-456", "doc.csv", "text/csv", b"a,b,c")
    basename = os.path.basename(ref.storage_path)
    # Expect format: <uuid>_doc.csv
    assert re.match(r"[0-9a-f-]{36}_doc\.csv", basename)


def test_save_file_data_integrity():
    from sme_copilot.services.file_storage import save_file as sf

    data = b"hello world this is test content"
    ref = sf("app-789", "test.pdf", "application/pdf", data)
    with open(ref.storage_path, "rb") as f:
        assert f.read() == data


# ---------------------------------------------------------------------------
# cleanup_files
# ---------------------------------------------------------------------------


def test_cleanup_removes_directory():
    from sme_copilot.services.file_storage import cleanup_files as cf
    from sme_copilot.services.file_storage import save_file as sf

    sf("app-cleanup", "f.pdf", "application/pdf", b"data")
    cf("app-cleanup")

    import sme_copilot.services.file_storage as fs_module

    assert not (fs_module.UPLOAD_DIR / "app-cleanup").exists()


def test_cleanup_nonexistent_is_noop():
    # Should not raise even if directory doesn't exist
    cleanup_files("app-does-not-exist-xyz")


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------


def test_max_files_constant():
    assert MAX_FILES == 5


def test_max_file_size_constant():
    assert MAX_FILE_SIZE == 25 * 1024 * 1024
