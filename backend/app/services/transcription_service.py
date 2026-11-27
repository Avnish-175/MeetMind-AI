from dataclasses import dataclass
from pathlib import Path
import threading
from typing import TYPE_CHECKING, Any

from app.core.config import settings

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

WAV_HEADER_MIN_BYTES = 44

_model_lock = threading.Lock()
_cached_model: "WhisperModel | None" = None
_cached_model_config: tuple[str, str, str, str | None] | None = None

_inference_lock = threading.Lock()


class TranscriptionError(Exception):
    """Raised when local Faster-Whisper transcription fails."""


@dataclass(frozen=True)
class TranscriptionResult:
    """Structured transcription output from Faster-Whisper."""

    full_text: str
    language: str | None
    language_probability: float | None
    duration_seconds: float | None
    model_name: str
    segments: list[dict[str, Any]]


def _get_whisper_config() -> tuple[str, str, str, str | None]:
    model_size = (settings.WHISPER_MODEL_SIZE or "small").strip()
    device = (settings.WHISPER_DEVICE or "cpu").strip()
    compute_type = (settings.WHISPER_COMPUTE_TYPE or "int8").strip()
    raw_root = settings.WHISPER_DOWNLOAD_ROOT
    download_root = raw_root.strip() if raw_root and raw_root.strip() else None
    return model_size, device, compute_type, download_root


def _get_whisper_model() -> tuple["WhisperModel", str]:
    """Lazily load and reuse the configured Faster-Whisper model."""
    global _cached_model, _cached_model_config

    config = _get_whisper_config()
    model_size, device, compute_type, download_root = config

    with _model_lock:
        if _cached_model is not None and _cached_model_config == config:
            return _cached_model, model_size

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscriptionError(
                "faster-whisper is not installed in the backend environment."
            ) from exc

        try:
            kwargs: dict[str, Any] = {
                "device": device,
                "compute_type": compute_type,
            }
            if download_root is not None:
                Path(download_root).mkdir(parents=True, exist_ok=True)
                kwargs["download_root"] = download_root

            model = WhisperModel(model_size, **kwargs)
        except Exception as exc:
            raise TranscriptionError(
                f"Failed to load Faster-Whisper model '{model_size}'."
            ) from exc

        _cached_model = model
        _cached_model_config = config
        return _cached_model, model_size


def transcribe_audio(audio_path: Path) -> TranscriptionResult:
    """Transcribe a normalized mono 16 kHz WAV file using local Faster-Whisper."""
    if not audio_path.is_file() or audio_path.stat().st_size <= WAV_HEADER_MIN_BYTES:
        raise TranscriptionError("Audio file for transcription is missing or empty.")

    model, model_name = _get_whisper_model()

    try:
        with _inference_lock:
            raw_segments, info = model.transcribe(
                str(audio_path),
                beam_size=5,
                vad_filter=True,
            )

            segments: list[dict[str, Any]] = []
            for idx, segment in enumerate(raw_segments, start=1):
                text = (segment.text or "").strip()
                if not text:
                    continue
                segments.append(
                    {
                        "id": idx,
                        "start": round(float(segment.start), 3),
                        "end": round(float(segment.end), 3),
                        "text": text,
                    }
                )

            language = getattr(info, "language", None)
            raw_prob = getattr(info, "language_probability", None)
            language_probability = round(float(raw_prob), 4) if raw_prob is not None else None
            raw_duration = getattr(info, "duration", None)
            duration_seconds = round(float(raw_duration), 3) if raw_duration is not None else None
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(
            "Local transcription failed while processing the audio stream."
        ) from exc

    full_text = " ".join(seg["text"] for seg in segments).strip()
    if not full_text:
        raise TranscriptionError(
            "No transcribable speech was detected in the meeting audio."
        )

    return TranscriptionResult(
        full_text=full_text,
        language=language,
        language_probability=language_probability,
        duration_seconds=duration_seconds,
        model_name=model_name,
        segments=segments,
    )
