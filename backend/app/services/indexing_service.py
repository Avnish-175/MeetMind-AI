import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.embedding_service import EmbeddingServiceError, generate_embeddings
from app.database.session import SessionLocal
from app.models.meeting import Meeting
from app.models.transcript import MeetingTranscript
from app.services.chunking_service import ChunkingError, chunk_transcript
from app.services.vector_store_service import (
    VectorStoreError,
    atomic_replace_meeting_embeddings,
    get_meeting_chunk_count,
)

logger = logging.getLogger(__name__)


def start_meeting_indexing_job(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> Meeting:
    """Validate ownership and transcript availability under a row lock, then mark the meeting as pending indexing."""
    stmt = (
        select(Meeting)
        .where(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        )
        .with_for_update()
    )
    meeting = db.scalar(stmt)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found.",
        )

    if meeting.embedding_status in ("pending", "processing"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Indexing is already in progress for this meeting.",
        )

    transcript = (
        db.query(MeetingTranscript)
        .filter(MeetingTranscript.meeting_id == meeting_id)
        .first()
    )
    if transcript is None or (
        not (transcript.full_text or "").strip() and not transcript.segments
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting must have a completed transcript before indexing.",
        )

    meeting.embedding_status = "pending"
    meeting.embedding_error = None
    db.commit()
    db.refresh(meeting)
    return meeting


def get_meeting_indexing_status(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Return the current embedding indexing status and chunk count for a user-owned meeting."""
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.user_id == user_id)
        .first()
    )
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found.",
        )

    chunk_count = get_meeting_chunk_count(meeting_id=meeting_id, user_id=user_id)

    return {
        "meeting_id": meeting.id,
        "embedding_status": meeting.embedding_status,
        "embedding_error": meeting.embedding_error,
        "indexed_at": meeting.indexed_at,
        "chunk_count": int(chunk_count),
    }


def process_meeting_indexing_task(meeting_id: int) -> None:
    """Background task that chunks the transcript, generates embeddings, and atomically updates ChromaDB.

    Existing embeddings are retained if generation or validation fails, preventing partial or corrupt state.
    """
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting is None:
            logger.error("Indexing task aborted: meeting %d not found.", meeting_id)
            return

        meeting.embedding_status = "processing"
        meeting.embedding_error = None
        db.commit()

        transcript = (
            db.query(MeetingTranscript)
            .filter(MeetingTranscript.meeting_id == meeting_id)
            .first()
        )
        if transcript is None:
            raise ChunkingError("Meeting transcript not found.")

        chunks = chunk_transcript(transcript)
        if not chunks:
            raise ChunkingError("Transcript produced no indexable text chunks.")

        texts = [c.content for c in chunks]
        vectors = generate_embeddings(texts)
        if len(vectors) != len(chunks):
            raise EmbeddingServiceError(
                f"Embedding count mismatch: expected {len(chunks)}, got {len(vectors)}."
            )

        items = [
            {
                "content": chunk.content,
                "embedding": vector,
                "chunk_index": chunk.chunk_index,
                "metadata": {
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "segment_ids": chunk.segment_ids,
                },
            }
            for chunk, vector in zip(chunks, vectors)
        ]

        stored_ids = atomic_replace_meeting_embeddings(
            meeting_id=meeting.id,
            user_id=meeting.user_id,
            items=items,
        )

        meeting.embedding_status = "completed"
        meeting.embedding_error = None
        meeting.indexed_at = func.now()
        db.commit()

        logger.info(
            "Successfully indexed %d chunks for meeting %d (user %d) in ChromaDB.",
            len(stored_ids),
            meeting.id,
            meeting.user_id,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Indexing failed for meeting %d: %s", meeting_id, exc)
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting is not None:
                meeting.embedding_status = "failed"
                meeting.embedding_error = str(exc)[:1000]
                db.commit()
        except Exception as status_exc:
            logger.error("Failed to persist indexing error status for meeting %d: %s", meeting_id, status_exc)
            db.rollback()
    finally:
        db.close()
