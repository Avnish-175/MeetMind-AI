from dataclasses import dataclass
from pathlib import Path
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import PROJECT_ROOT, settings

CHUNK_SIZE_BYTES = 1024 * 1024  # 1 MB streaming chunks

# Mapping of allowed lowercase extensions to (media_type, allowed_mime_types)
ALLOWED_MEDIA_FORMATS: dict[str, tuple[str, set[str]]] = {
    ".mp3": ("audio", {"audio/mpeg", "audio/mp3"}),
    ".wav": ("audio", {"audio/wav", "audio/x-wav", "audio/wave"}),
    ".m4a": ("audio", {"audio/mp4", "audio/x-m4a", "audio/m4a"}),
    ".ogg": ("audio", {"audio/ogg", "application/ogg"}),
    ".flac": ("audio", {"audio/flac", "audio/x-flac"}),
    ".aac": ("audio", {"audio/aac"}),
    ".mp4": ("video", {"video/mp4"}),
    ".webm": ("video", {"video/webm", "audio/webm"}),
    ".mov": ("video", {"video/quicktime"}),
    ".mkv": ("video", {"video/x-matroska"}),
    ".avi": ("video", {"video/x-msvideo", "video/avi"}),
}


@dataclass(frozen=True)
class StoredMediaFile:
    """Metadata returned after safely streaming an uploaded media file to disk."""

    storage_path: str
    original_filename: str
    media_type: str
    mime_type: str
    file_size_bytes: int


def _get_upload_dir() -> Path:
    """Resolve and ensure the local upload directory exists."""
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _sanitize_original_filename(filename: str | None) -> str:
    """Strip directory components and validate the uploaded filename."""
    if not filename or "\x00" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid filename is required.",
        )
    safe_name = Path(filename).name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid filename is required.",
        )
    return safe_name[:255]


def _validate_media_format(original_filename: str, content_type: str | None) -> tuple[str, str, str]:
    """Validate file extension and MIME type against supported audio/video formats."""
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_MEDIA_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported media file extension.",
        )

    expected_media_type, allowed_mimes = ALLOWED_MEDIA_FORMATS[extension]
    normalized_mime = (content_type or "").split(";")[0].strip().lower()

    if normalized_mime not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported or mismatched media MIME type.",
        )

    media_type = "audio" if normalized_mime == "audio/webm" else expected_media_type
    return extension, media_type, normalized_mime


async def save_upload_file(upload_file: UploadFile) -> StoredMediaFile:
    """Stream an uploaded audio/video file to local storage with strict validation."""
    original_filename = _sanitize_original_filename(upload_file.filename)
    extension, media_type, mime_type = _validate_media_format(
        original_filename,
        upload_file.content_type,
    )

    upload_dir = _get_upload_dir()
    server_filename = f"{uuid.uuid4().hex}{extension}"
    target_path = (upload_dir / server_filename).resolve()

    if target_path.parent != upload_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid storage destination.",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0

    try:
        with target_path.open("wb") as buffer:
            while True:
                chunk = await upload_file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                    )
                buffer.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    except OSError:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded media file.",
        )
    finally:
        await upload_file.close()

    try:
        relative_storage_path = target_path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        relative_storage_path = server_filename

    return StoredMediaFile(
        storage_path=relative_storage_path,
        original_filename=original_filename,
        media_type=media_type,
        mime_type=mime_type,
        file_size_bytes=total_bytes,
    )


def delete_stored_file(storage_path: str) -> None:
    """Safely remove a stored media file from the local upload directory."""
    if not storage_path:
        return

    upload_dir = _get_upload_dir()
    candidate = Path(storage_path)
    resolved = (
        (PROJECT_ROOT / candidate).resolve()
        if not candidate.is_absolute()
        else candidate.resolve()
    )

    if resolved.parent != upload_dir:
        return

    resolved.unlink(missing_ok=True)
