from collections.abc import Iterator
from contextlib import contextmanager
import logging
from pathlib import Path
import shutil
import subprocess
import tempfile

from app.core.config import PROJECT_ROOT, settings
from app.services.storage_service import ALLOWED_MEDIA_FORMATS

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT_SECONDS = 600
WAV_HEADER_MIN_BYTES = 44


class MediaProcessingError(Exception):
    """Raised when media validation or FFmpeg audio extraction fails."""


def _resolve_ffmpeg_executable() -> str:
    """Resolve and verify the configured FFmpeg binary path."""
    configured = (settings.FFMPEG_PATH or "ffmpeg").strip()
    if not configured:
        configured = "ffmpeg"

    resolved = shutil.which(configured)
    if resolved is None:
        raise MediaProcessingError(
            "FFmpeg executable was not found. Install FFmpeg and set FFMPEG_PATH."
        )
    return resolved


def resolve_stored_media_path(storage_path: str) -> Path:
    """Resolve a stored media path and guard against path traversal."""
    if not storage_path or "\x00" in storage_path:
        raise MediaProcessingError("Invalid media storage path.")

    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    candidate = Path(storage_path)
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (PROJECT_ROOT / candidate).resolve()
    )

    if resolved.parent != upload_dir:
        raise MediaProcessingError("Media path is outside the allowed upload directory.")

    if not resolved.is_file():
        raise MediaProcessingError("Uploaded media file could not be found on disk.")

    if resolved.suffix.lower() not in ALLOWED_MEDIA_FORMATS:
        raise MediaProcessingError("Unsupported media file extension.")

    return resolved


@contextmanager
def extract_normalized_audio(storage_path: str) -> Iterator[Path]:
    """Extract and normalize meeting media to mono 16 kHz WAV in a temporary directory.

    The original uploaded file is preserved, and temporary files are always removed
    when the context exits.
    """
    source_path = resolve_stored_media_path(storage_path)
    ffmpeg_executable = _resolve_ffmpeg_executable()

    with tempfile.TemporaryDirectory(prefix="meetmind_audio_") as temp_dir:
        output_wav_path = Path(temp_dir) / f"{source_path.stem}_16k_mono.wav"
        command = [
            ffmpeg_executable,
            "-y",
            "-nostdin",
            "-i",
            str(source_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_wav_path),
        ]

        logger.info(
            "Starting FFmpeg audio extraction for source '%s' to '%s'",
            source_path.name,
            output_wav_path.name,
        )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=False,
                timeout=FFMPEG_TIMEOUT_SECONDS,
                check=False,
            )
            logger.info(
                "FFmpeg audio extraction completed for '%s' with return code %d",
                source_path.name,
                result.returncode,
            )
        except FileNotFoundError as exc:
            logger.error(
                "FFmpeg audio extraction failed: executable not found at '%s'",
                ffmpeg_executable,
                exc_info=True,
            )
            raise MediaProcessingError(
                "FFmpeg executable was not found. Install FFmpeg and set FFMPEG_PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            logger.error(
                "FFmpeg audio extraction timed out after %d seconds for '%s'",
                FFMPEG_TIMEOUT_SECONDS,
                source_path.name,
                exc_info=True,
            )
            raise MediaProcessingError(
                "Media audio extraction timed out while running FFmpeg."
            ) from exc
        except OSError as exc:
            logger.error(
                "FFmpeg audio extraction failed to execute for '%s': %s",
                source_path.name,
                exc,
                exc_info=True,
            )
            raise MediaProcessingError(
                "Failed to execute FFmpeg for media audio extraction."
            ) from exc

        if result.returncode != 0:
            stderr_lower = (result.stderr or "").lower()
            logger.error(
                "FFmpeg audio extraction failed for '%s' (exit code %d). Stderr: %s",
                source_path.name,
                result.returncode,
                (result.stderr or "").strip(),
            )
            if "does not contain any stream" in stderr_lower or "no audio" in stderr_lower:
                raise MediaProcessingError(
                    "The uploaded media file does not contain an audio stream."
                )
            raise MediaProcessingError(
                "FFmpeg failed to extract audio from the media file. The file may be corrupt or unsupported."
            )

        if not output_wav_path.is_file() or output_wav_path.stat().st_size <= WAV_HEADER_MIN_BYTES:
            logger.error(
                "Extracted audio file '%s' is missing or smaller than WAV header minimum size",
                output_wav_path.name,
            )
            raise MediaProcessingError(
                "Extracted audio output is empty or invalid."
            )

        yield output_wav_path
