"""Upload validation and safe storage. User-supplied names are never used as paths."""
import hashlib
import re
import uuid
from pathlib import Path

from app.config import settings
from app.errors import AppError

ALLOWED = {
    ".pdf": ("application/pdf", b"%PDF"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".txt": ("text/plain", b""),
}


def sanitize_filename(name: str) -> str:
    base = re.split(r"[\\/]", name or "upload")[-1]
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base)[:120].strip(" .")
    return base or "upload"


def validate_upload(filename: str, declared_mime: str | None, data: bytes) -> tuple[str, str]:
    """Return (extension, canonical_mime) or raise AppError 413/415."""
    if len(data) > settings.max_upload_bytes:
        raise AppError(413, "FILE_TOO_LARGE", f"File exceeds {settings.max_upload_bytes // (1024 * 1024)} MB limit.")
    if not data:
        raise AppError(422, "EMPTY_FILE", "The uploaded file is empty.")
    ext = Path(sanitize_filename(filename)).suffix.lower()
    if ext not in ALLOWED:
        raise AppError(415, "UNSUPPORTED_FILE_TYPE", "Only PDF, PNG, JPEG and TXT files are supported.")
    mime, magic = ALLOWED[ext]
    base_declared = (declared_mime or "").split(";")[0].strip().lower()
    if base_declared and base_declared not in (mime, "application/octet-stream"):
        raise AppError(415, "MIME_MISMATCH", "File type does not match its extension.")
    if magic and not data.startswith(magic):
        raise AppError(415, "INVALID_FILE_SIGNATURE", "File content does not match its extension.")
    if ext == ".txt":
        if b"\x00" in data[:4096]:
            raise AppError(415, "INVALID_FILE_SIGNATURE", "Text file contains binary data.")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise AppError(415, "INVALID_TEXT_ENCODING", "Text files must be UTF-8.") from None
    return ext, mime


def store_bytes(data: bytes, ext: str) -> tuple[str, str]:
    """Persist under a generated key. Returns (storage_key, sha256)."""
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    key = f"{uuid.uuid4().hex}{ext}"
    (settings.storage_dir / key).write_bytes(data)
    return key, hashlib.sha256(data).hexdigest()


def path_for(storage_key: str) -> Path:
    p = (settings.storage_dir / storage_key).resolve()
    if settings.storage_dir.resolve() not in p.parents:  # defence in depth against traversal
        raise AppError(404, "NOT_FOUND", "File not found.")
    return p
