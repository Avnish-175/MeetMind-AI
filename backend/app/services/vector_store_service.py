import json
import logging
import math
import os
import threading
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.core.config import settings

logger = logging.getLogger(__name__)

_chroma_client: ClientAPI | None = None
_chroma_lock = threading.Lock()


class VectorStoreError(Exception):
    """Base exception for vector storage and retrieval errors."""


class VectorValidationError(VectorStoreError, ValueError):
    """Raised when vector dimensions, content, or parameters are invalid."""


def get_chroma_client() -> ClientAPI:
    """Lazily initialize and return the ChromaDB PersistentClient."""
    global _chroma_client
    with _chroma_lock:
        if _chroma_client is None:
            os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
            logger.info(
                "Initializing ChromaDB PersistentClient at '%s'...",
                settings.CHROMA_PERSIST_DIRECTORY,
            )
            _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
        return _chroma_client


def get_meeting_collection() -> Collection:
    """Retrieve or create the meeting chunks collection configured with cosine distance."""
    client = get_chroma_client()
    try:
        return client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as exc:
        logger.error(
            "Failed to access ChromaDB collection '%s': %s",
            settings.CHROMA_COLLECTION_NAME,
            exc,
        )
        raise VectorStoreError(f"Failed to access ChromaDB collection: {exc}") from exc


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


def _serialize_metadata(
    meeting_id: int,
    user_id: int,
    chunk_index: int,
    raw_metadata: dict[str, Any] | None = None,
) -> dict[str, str | int | float | bool]:
    """Serialize chunk metadata into types accepted by ChromaDB (primitive scalars)."""
    meta: dict[str, str | int | float | bool] = {
        "meeting_id": int(meeting_id),
        "user_id": int(user_id),
        "chunk_index": int(chunk_index),
    }
    if raw_metadata:
        for k, v in raw_metadata.items():
            if isinstance(v, (int, float, bool, str)):
                meta[k] = v
            elif v is None:
                continue
            else:
                meta[k] = json.dumps(v)
    return meta


def _deserialize_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Deserialize metadata retrieved from ChromaDB, restoring complex types like segment_ids."""
    if not meta:
        return {}
    deserialized: dict[str, Any] = dict(meta)
    if "segment_ids" in deserialized and isinstance(deserialized["segment_ids"], str):
        try:
            deserialized["segment_ids"] = json.loads(deserialized["segment_ids"])
        except Exception:
            deserialized["segment_ids"] = []
    return deserialized


def store_embedding(
    meeting_id: int,
    user_id: int,
    content: str,
    embedding: list[float],
    chunk_index: int = 0,
    metadata: dict[str, Any] | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Persist a single meeting chunk embedding in ChromaDB."""
    clean_content = _validate_content(content)
    clean_vector = _validate_vector(embedding)
    if chunk_index < 0:
        raise VectorValidationError("chunk_index must be non-negative.")

    doc_id = f"m_{meeting_id}_u_{user_id}_c_{chunk_index}"
    chroma_meta = _serialize_metadata(meeting_id, user_id, chunk_index, metadata)

    collection = get_meeting_collection()
    try:
        collection.upsert(
            ids=[doc_id],
            embeddings=[clean_vector],
            documents=[clean_content],
            metadatas=[chroma_meta],
        )
        logger.info(
            "Stored embedding %s in ChromaDB for meeting %d (user %d, chunk %d)",
            doc_id,
            meeting_id,
            user_id,
            chunk_index,
        )
        return {
            "id": doc_id,
            "meeting_id": meeting_id,
            "user_id": user_id,
            "chunk_index": chunk_index,
            "content": clean_content,
        }
    except Exception as exc:
        logger.error("Failed to store embedding in ChromaDB: %s", exc)
        raise VectorStoreError(f"Failed to store embedding in ChromaDB: {exc}") from exc


def store_embeddings_batch(
    meeting_id: int,
    user_id: int,
    items: list[dict[str, Any]],
    db: Any = None,
) -> list[str]:
    """Persist multiple chunk embeddings for a meeting in ChromaDB.

    Each item in `items` must contain:
      - `content`: str
      - `embedding`: list[float]
      - `chunk_index`: int (optional, defaults to item position)
      - `metadata`: dict[str, Any] | None (optional)
    """
    if not isinstance(items, list) or len(items) == 0:
        raise VectorValidationError("Batch items must be a non-empty list.")

    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

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

        doc_id = f"m_{meeting_id}_u_{user_id}_c_{chunk_index}"
        chroma_meta = _serialize_metadata(meeting_id, user_id, chunk_index, metadata)

        ids.append(doc_id)
        embeddings.append(clean_vector)
        documents.append(clean_content)
        metadatas.append(chroma_meta)

    collection = get_meeting_collection()
    try:
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(
            "Stored %d embeddings in batch in ChromaDB for meeting %d (user %d)",
            len(ids),
            meeting_id,
            user_id,
        )
        return ids
    except Exception as exc:
        logger.error("Failed to store batch embeddings in ChromaDB: %s", exc)
        raise VectorStoreError(f"Failed to store batch embeddings in ChromaDB: {exc}") from exc


def delete_meeting_embeddings(
    meeting_id: int,
    user_id: int,
    db: Any = None,
) -> int:
    """Delete all embeddings for a meeting owned by `user_id` from ChromaDB. Returns count."""
    collection = get_meeting_collection()
    where_filter = {
        "$and": [
            {"meeting_id": int(meeting_id)},
            {"user_id": int(user_id)},
        ]
    }
    try:
        existing = collection.get(where=where_filter)
        existing_ids = existing.get("ids", [])
        if existing_ids:
            collection.delete(ids=existing_ids)
            logger.info(
                "Deleted %d embeddings from ChromaDB for meeting %d (user %d)",
                len(existing_ids),
                meeting_id,
                user_id,
            )
            return len(existing_ids)
        return 0
    except Exception as exc:
        logger.error("Failed to delete embeddings from ChromaDB: %s", exc)
        raise VectorStoreError(f"Failed to delete embeddings from ChromaDB: {exc}") from exc


def atomic_replace_meeting_embeddings(
    meeting_id: int,
    user_id: int,
    items: list[dict[str, Any]],
) -> list[str]:
    """Atomically upsert new chunk embeddings and clean up any obsolete chunk IDs.

    Validates all data and upserts new chunks before deleting any obsolete chunk IDs
    from prior runs, ensuring an interrupted or failed indexing attempt does not leave
    the meeting without searchable vectors.
    """
    collection = get_meeting_collection()
    where_filter = {
        "$and": [
            {"meeting_id": int(meeting_id)},
            {"user_id": int(user_id)},
        ]
    }

    try:
        existing = collection.get(where=where_filter)
        old_ids = set(existing.get("ids", []))
    except Exception as exc:
        logger.warning("Could not fetch pre-existing chunk IDs from ChromaDB: %s", exc)
        old_ids = set()

    # Store the validated new batch
    new_ids = store_embeddings_batch(meeting_id=meeting_id, user_id=user_id, items=items)

    # Prune any IDs that were present in a previous run but not in this run
    stale_ids = list(old_ids - set(new_ids))
    if stale_ids:
        try:
            collection.delete(ids=stale_ids)
            logger.info(
                "Pruned %d stale embedding vectors for meeting %d in ChromaDB",
                len(stale_ids),
                meeting_id,
            )
        except Exception as exc:
            logger.warning("Failed to prune stale IDs from ChromaDB: %s", exc)

    return new_ids


def get_meeting_chunk_count(meeting_id: int, user_id: int) -> int:
    """Return the total number of indexed chunks stored in ChromaDB for a meeting."""
    try:
        collection = get_meeting_collection()
        where_filter = {
            "$and": [
                {"meeting_id": int(meeting_id)},
                {"user_id": int(user_id)},
            ]
        }
        res = collection.get(where=where_filter)
        return len(res.get("ids", []))
    except Exception as exc:
        logger.error("Failed to get chunk count from ChromaDB: %s", exc)
        return 0


def search_similar_embeddings(
    query_embedding: list[float],
    user_id: int,
    top_k: int = 5,
    meeting_id: int | None = None,
    db: Any = None,
) -> list[dict[str, Any]]:
    """Search for semantically similar meeting chunks using ChromaDB cosine similarity.

    Always enforces `user_id` ownership filtering. If `meeting_id` is provided,
    results are further restricted to that meeting owned by `user_id`.
    """
    clean_query = _validate_vector(query_embedding)
    if top_k <= 0:
        raise VectorValidationError("top_k must be a positive integer.")

    collection = get_meeting_collection()

    try:
        total_count = collection.count()
        if total_count == 0:
            return []

        if meeting_id is not None:
            where_filter: dict[str, Any] = {
                "$and": [
                    {"user_id": int(user_id)},
                    {"meeting_id": int(meeting_id)},
                ]
            }
        else:
            where_filter = {"user_id": int(user_id)}

        effective_k = min(top_k, total_count)
        query_response = collection.query(
            query_embeddings=[clean_query],
            n_results=effective_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.error("ChromaDB query failed: %s", exc)
        raise VectorStoreError(f"ChromaDB query failed: {exc}") from exc

    ids_list = query_response.get("ids", [[]])
    docs_list = query_response.get("documents", [[]])
    metas_list = query_response.get("metadatas", [[]])
    distances_list = query_response.get("distances", [[]])

    if not ids_list or not ids_list[0]:
        return []

    ids = ids_list[0]
    docs = docs_list[0] if docs_list else []
    metas = metas_list[0] if metas_list else []
    distances = distances_list[0] if distances_list else []

    results: list[dict[str, Any]] = []
    for doc_id, doc, raw_meta, dist in zip(ids, docs, metas, distances):
        meta = _deserialize_metadata(raw_meta or {})
        distance = float(dist) if dist is not None else 1.0
        # Cosine distance in ChromaDB is in [0, 2]; similarity = 1.0 - distance
        similarity_score = max(0.0, min(1.0, 1.0 - distance))

        results.append(
            {
                "id": doc_id,
                "meeting_id": int(meta.get("meeting_id", meeting_id or 0)),
                "content": str(doc),
                "chunk_index": int(meta.get("chunk_index", 0)),
                "metadata": meta,
                "similarity_score": similarity_score,
            }
        )

    return results
