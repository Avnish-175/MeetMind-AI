import logging
import math
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.meeting import Meeting
from app.models.meeting_embedding import MeetingEmbedding

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Base exception for vector storage and retrieval errors."""


class VectorValidationError(VectorStoreError, ValueError):
    """Raised when vector dimensions, content, or parameters are invalid."""


def _validate_vector(embedding: list[float]) -> list[float]:
    """Validate that an embedding is a finite numeric list matching the configured dimension."""
    if not isinstance(embedding, list):
        raise VectorValidationError(
            f"Embedding must be a list of floats, got {type(embedding).__name__}."
        )

    expected_dim = int(settings.EMBEDDING_DIMENSION)
    if len(embedding) != expected_dim:
        raise VectorValidationError(
            f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}."
        )

    validated: list[float] = []
    for idx, val in enumerate(embedding):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise VectorValidationError(
                f"Embedding element at index {idx} must be numeric, got {type(val).__name__}."
            )
        fval = float(val)
        if not math.isfinite(fval):
            raise VectorValidationError(
                f"Embedding element at index {idx} is not finite ({val})."
            )
        validated.append(fval)

    return validated


def _validate_content(content: str) -> str:
    """Validate that chunk content is a non-empty string."""
    if not isinstance(content, str) or not content.strip():
        raise VectorValidationError("Chunk content must be a non-empty string.")
    return content.strip()


def _verify_meeting_ownership(db: Session, meeting_id: int, user_id: int) -> None:
    """Ensure the target meeting exists and belongs to the specified user."""
    stmt = select(Meeting.id).where(
        Meeting.id == meeting_id,
        Meeting.user_id == user_id,
    )
    if db.execute(stmt).scalar_one_or_none() is None:
        raise VectorStoreError(
            f"Meeting {meeting_id} not found or does not belong to user {user_id}."
        )


def store_embedding(
    db: Session,
    meeting_id: int,
    user_id: int,
    content: str,
    embedding: list[float],
    chunk_index: int = 0,
    metadata: dict[str, Any] | None = None,
) -> MeetingEmbedding:
    """Persist a single meeting chunk embedding after validating ownership and dimensions."""
    _verify_meeting_ownership(db, meeting_id, user_id)
    clean_content = _validate_content(content)
    clean_vector = _validate_vector(embedding)

    if chunk_index < 0:
        raise VectorValidationError("chunk_index must be non-negative.")

    record = MeetingEmbedding(
        meeting_id=meeting_id,
        user_id=user_id,
        content=clean_content,
        embedding=clean_vector,
        chunk_index=chunk_index,
        chunk_metadata=metadata,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(
        "Stored embedding %d for meeting %d (user %d, chunk %d)",
        record.id,
        meeting_id,
        user_id,
        chunk_index,
    )
    return record


def store_embeddings_batch(
    db: Session,
    meeting_id: int,
    user_id: int,
    items: list[dict[str, Any]],
) -> list[MeetingEmbedding]:
    """Persist multiple chunk embeddings for a meeting in a single transaction.

    Each item in `items` must contain:
      - `content`: str
      - `embedding`: list[float]
      - `chunk_index`: int (optional, defaults to item position)
      - `metadata`: dict[str, Any] | None (optional)
    """
    if not isinstance(items, list) or len(items) == 0:
        raise VectorValidationError("Batch items must be a non-empty list.")

    _verify_meeting_ownership(db, meeting_id, user_id)

    records: list[MeetingEmbedding] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise VectorValidationError(f"Batch item at index {idx} must be a dict.")
        clean_content = _validate_content(item.get("content", ""))
        clean_vector = _validate_vector(item.get("embedding", []))
        chunk_index = item.get("chunk_index", idx)
        if not isinstance(chunk_index, int) or chunk_index < 0:
            raise VectorValidationError(
                f"Invalid chunk_index at batch index {idx}: {chunk_index}"
            )
        metadata = item.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise VectorValidationError(
                f"metadata at batch index {idx} must be a dict or None."
            )

        records.append(
            MeetingEmbedding(
                meeting_id=meeting_id,
                user_id=user_id,
                content=clean_content,
                embedding=clean_vector,
                chunk_index=chunk_index,
                chunk_metadata=metadata,
            )
        )

    db.add_all(records)
    db.commit()
    for rec in records:
        db.refresh(rec)

    logger.info(
        "Stored %d embeddings in batch for meeting %d (user %d)",
        len(records),
        meeting_id,
        user_id,
    )
    return records


def delete_meeting_embeddings(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> int:
    """Delete all embeddings for a meeting owned by `user_id`. Returns deleted row count."""
    stmt = delete(MeetingEmbedding).where(
        MeetingEmbedding.meeting_id == meeting_id,
        MeetingEmbedding.user_id == user_id,
    )
    result = db.execute(stmt)
    db.commit()
    deleted_count = int(result.rowcount or 0)
    logger.info(
        "Deleted %d embeddings for meeting %d (user %d)",
        deleted_count,
        meeting_id,
        user_id,
    )
    return deleted_count


def search_similar_embeddings(
    db: Session,
    query_embedding: list[float],
    user_id: int,
    top_k: int = 5,
    meeting_id: int | None = None,
) -> list[dict[str, Any]]:
    """Search for semantically similar meeting chunks using pgvector cosine distance.

    Always enforces `user_id` ownership filtering. If `meeting_id` is provided,
    results are further restricted to that meeting owned by `user_id`.
    """
    clean_query = _validate_vector(query_embedding)
    if top_k <= 0:
        raise VectorValidationError("top_k must be a positive integer.")

    distance_expr = MeetingEmbedding.embedding.cosine_distance(clean_query).label("distance")

    stmt = (
        select(
            MeetingEmbedding.id,
            MeetingEmbedding.meeting_id,
            MeetingEmbedding.content,
            MeetingEmbedding.chunk_index,
            MeetingEmbedding.chunk_metadata,
            distance_expr,
        )
        .where(MeetingEmbedding.user_id == user_id)
    )

    if meeting_id is not None:
        stmt = stmt.where(MeetingEmbedding.meeting_id == meeting_id)

    stmt = stmt.order_by(distance_expr.asc()).limit(top_k)

    rows = db.execute(stmt).all()
    results: list[dict[str, Any]] = []
    for row in rows:
        distance = float(row.distance)
        similarity_score = max(0.0, min(1.0, 1.0 - distance))
        results.append(
            {
                "id": row.id,
                "meeting_id": row.meeting_id,
                "content": row.content,
                "chunk_index": row.chunk_index,
                "metadata": row.chunk_metadata,
                "similarity_score": similarity_score,
            }
        )

    return results
