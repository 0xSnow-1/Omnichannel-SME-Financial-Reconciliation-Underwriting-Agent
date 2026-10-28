import shutil
import uuid
from pathlib import Path

from sme_copilot.schemas.models import FileRef

UPLOAD_DIR = Path("data/uploads")
ALLOWED_TYPES = {
    "application/pdf",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
MAX_FILES = 5


def validate_file(filename: str, content_type: str, size: int) -> str | None:
    """Return error message if invalid, None if valid."""
    if content_type not in ALLOWED_TYPES:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return f"Unsupported file type: {ext}"
    if size > MAX_FILE_SIZE:
        return "File exceeds 25 MB limit"
    return None


def save_file(app_id: str, filename: str, content_type: str, data: bytes) -> FileRef:
    app_dir = UPLOAD_DIR / app_id
    app_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_name = f"{file_id}_{filename}"
    path = app_dir / safe_name
    path.write_bytes(data)
    return FileRef(
        filename=filename,
        content_type=content_type,
        size_bytes=len(data),
        storage_path=str(path),
    )


def cleanup_files(app_id: str) -> None:
    app_dir = UPLOAD_DIR / app_id
    if app_dir.exists():
        shutil.rmtree(app_dir)
