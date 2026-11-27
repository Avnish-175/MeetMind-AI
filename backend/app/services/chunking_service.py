from dataclasses import dataclass
import logging
from typing import Any

from app.core.config import settings
from app.models.transcript import MeetingTranscript

logger = logging.getLogger(__name__)


class ChunkingError(Exception):
    """Raised when transcript chunking fails due to invalid configuration or input."""


@dataclass
class TranscriptChunk:
    """A semantically coherent chunk of transcript segments with preserved provenance."""

    chunk_index: int
    content: str
    start_time: float | None
    end_time: float | None
    segment_ids: list[int]


def _normalize_segments(raw_segments: Any) -> list[dict[str, Any]]:
    """Filter and normalize raw transcript segment dicts without dropping valid text."""
    if not isinstance(raw_segments, list):
        return []

    normalized: list[dict[str, Any]] = []
    for idx, seg in enumerate(raw_segments):
        if not isinstance(seg, dict):
            continue
        text = str(seg.get("text", "")).strip()
        if not text:
            continue

        seg_id = seg.get("id")
        if not isinstance(seg_id, int):
            seg_id = idx

        start_val = seg.get("start")
        end_val = seg.get("end")
        start_time = float(start_val) if isinstance(start_val, (int, float)) else None
        end_time = float(end_val) if isinstance(end_val, (int, float)) else None

        normalized.append(
            {
                "id": seg_id,
                "start": start_time,
                "end": end_time,
                "text": text,
            }
        )
    return normalized


def _build_chunk_from_segments(
    chunk_index: int,
    segs: list[dict[str, Any]],
) -> TranscriptChunk:
    """Construct a TranscriptChunk from a non-empty list of normalized segments."""
    content = " ".join(s["text"] for s in segs).strip()
    start_times = [s["start"] for s in segs if s["start"] is not None]
    end_times = [s["end"] for s in segs if s["end"] is not None]
    segment_ids = [s["id"] for s in segs]

    return TranscriptChunk(
        chunk_index=chunk_index,
        content=content,
        start_time=start_times[0] if start_times else None,
        end_time=end_times[-1] if end_times else None,
        segment_ids=segment_ids,
    )


def _compute_overlap_tail(
    segs: list[dict[str, Any]],
    overlap_chars: int,
) -> list[dict[str, Any]]:
    """Return trailing segments for overlap while guaranteeing forward progress."""
    if overlap_chars <= 0 or len(segs) <= 1:
        return []

    tail: list[dict[str, Any]] = []
    char_count = 0
    # Never keep all segments (index 0 must be dropped to guarantee progress)
    for seg in reversed(segs[1:]):
        seg_len = len(seg["text"]) + 1
        if tail and char_count + seg_len > overlap_chars:
            break
        tail.insert(0, seg)
        char_count += seg_len
        if char_count >= overlap_chars:
            break

    return tail


def _chunk_plain_text(
    full_text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TranscriptChunk]:
    """Fallback chunker when timestamped segments are absent."""
    cleaned = full_text.strip()
    if not cleaned:
        return []

    chunks: list[TranscriptChunk] = []
    start = 0
    chunk_idx = 0
    text_len = len(cleaned)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # Try to break at a whitespace boundary
            space_idx = cleaned.rfind(" ", start + chunk_size // 2, end)
            if space_idx != -1:
                end = space_idx

        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(
                TranscriptChunk(
                    chunk_index=chunk_idx,
                    content=piece,
                    start_time=None,
                    end_time=None,
                    segment_ids=[],
                )
            )
            chunk_idx += 1

        if end >= text_len:
            break

        next_start = max(start + 1, end - chunk_overlap)
        start = next_start

    return chunks


def chunk_transcript(
    transcript: MeetingTranscript | None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[TranscriptChunk]:
    """Divide a MeetingTranscript into overlapping chunks preserving segment IDs and timestamps."""
    if transcript is None:
        return []

    resolved_size = int(chunk_size if chunk_size is not None else settings.RAG_CHUNK_SIZE)
    resolved_overlap = int(
        chunk_overlap if chunk_overlap is not None else settings.RAG_CHUNK_OVERLAP
    )

    if resolved_size <= 0:
        raise ChunkingError("chunk_size must be a positive integer.")
    if resolved_overlap < 0 or resolved_overlap >= resolved_size:
        raise ChunkingError("chunk_overlap must be non-negative and less than chunk_size.")

    segments = _normalize_segments(transcript.segments)
    if not segments:
        return _chunk_plain_text(
            transcript.full_text or "",
            chunk_size=resolved_size,
            chunk_overlap=resolved_overlap,
        )

    chunks: list[TranscriptChunk] = []
    current_segs: list[dict[str, Any]] = []
    current_chars = 0

    for seg in segments:
        seg_len = len(seg["text"]) + (1 if current_segs else 0)
        if current_segs and current_chars + seg_len > resolved_size:
            chunks.append(_build_chunk_from_segments(len(chunks), current_segs))
            overlap_segs = _compute_overlap_tail(current_segs, resolved_overlap)
            current_segs = list(overlap_segs)
            current_chars = sum(len(s["text"]) for s in current_segs) + max(
                0, len(current_segs) - 1
            )

        current_segs.append(seg)
        current_chars += len(seg["text"]) + (1 if len(current_segs) > 1 else 0)

    if current_segs:
        chunks.append(_build_chunk_from_segments(len(chunks), current_segs))

    logger.info(
        "Chunked transcript for meeting %s into %d chunks (from %d segments).",
        transcript.meeting_id,
        len(chunks),
        len(segments),
    )
    return chunks
