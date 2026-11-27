import logging
import threading
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_cached_model: Any = None
_cached_model_name: str | None = None
_cached_device: str | None = None


class EmbeddingServiceError(Exception):
    """Base exception for local embedding operations and model errors."""


class EmbeddingValidationError(EmbeddingServiceError, ValueError):
    """Raised when text inputs for embeddings are invalid, empty, or improperly typed."""


def is_embedding_model_loaded() -> bool:
    """Check whether the SentenceTransformer model has been loaded into memory."""
    return _cached_model is not None


def get_embedding_dimension() -> int:
    """Retrieve the configured embedding vector dimension."""
    return int(settings.EMBEDDING_DIMENSION)


def get_embedding_model(
    model_name: str | None = None,
    device: str | None = None,
) -> Any:
    """Lazily load and cache the SentenceTransformer model.

    The model is loaded thread-safely on first use and cached in memory.
    Startup remains fast and non-blocking because no model is loaded until needed.
    """
    global _cached_model, _cached_model_name, _cached_device

    resolved_model_name = (model_name or settings.EMBEDDING_MODEL_NAME).strip()
    resolved_device = (device or getattr(settings, "EMBEDDING_DEVICE", "cpu")).strip().lower()

    with _model_lock:
        if (
            _cached_model is not None
            and _cached_model_name == resolved_model_name
            and _cached_device == resolved_device
        ):
            return _cached_model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            logger.error("sentence-transformers is not installed in the environment: %s", exc)
            raise EmbeddingServiceError(
                "sentence-transformers is not installed. Please install it using requirements.txt."
            ) from exc

        try:
            logger.info(
                "Loading SentenceTransformer embedding model '%s' on device '%s'...",
                resolved_model_name,
                resolved_device,
            )
            model = SentenceTransformer(resolved_model_name, device=resolved_device)
            _cached_model = model
            _cached_model_name = resolved_model_name
            _cached_device = resolved_device
            logger.info("SentenceTransformer model '%s' loaded successfully.", resolved_model_name)
            return _cached_model
        except Exception as exc:
            logger.error("Failed to load SentenceTransformer model '%s': %s", resolved_model_name, exc)
            raise EmbeddingServiceError(
                f"Failed to load embedding model '{resolved_model_name}': {exc}"
            ) from exc


def generate_embedding(
    text: str,
    model_name: str | None = None,
    device: str | None = None,
) -> list[float]:
    """Generate a normalized embedding vector for a single text string.

    Args:
        text: Non-empty input string to embed.
        model_name: Optional model identifier override.
        device: Optional execution device override (defaults to configured device, e.g. 'cpu').

    Returns:
        A list of floating-point numbers representing the normalized embedding vector.

    Raises:
        EmbeddingValidationError: If text is empty, whitespace-only, or not a string.
        EmbeddingServiceError: If model loading or inference fails.
    """
    if not isinstance(text, str):
        raise EmbeddingValidationError(f"Expected text to be a string, got {type(text).__name__}.")

    stripped_text = text.strip()
    if not stripped_text:
        raise EmbeddingValidationError("Input text cannot be empty or whitespace-only.")

    model = get_embedding_model(model_name=model_name, device=device)

    try:
        embedding = model.encode(
            stripped_text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if hasattr(embedding, "tolist"):
            return [float(x) for x in embedding.tolist()]
        return [float(x) for x in embedding]
    except Exception as exc:
        logger.error("Failed to generate embedding for text: %s", exc)
        raise EmbeddingServiceError(f"Embedding inference failed: {exc}") from exc


def generate_embeddings(
    texts: list[str],
    model_name: str | None = None,
    device: str | None = None,
    batch_size: int = 32,
) -> list[list[float]]:
    """Generate normalized embedding vectors for a batch of text strings, preserving order.

    Args:
        texts: Non-empty list of non-empty strings to embed.
        model_name: Optional model identifier override.
        device: Optional execution device override (defaults to configured device, e.g. 'cpu').
        batch_size: Batch size for model inference.

    Returns:
        A list of lists of floating-point numbers matching the exact input order.

    Raises:
        EmbeddingValidationError: If texts is not a list, is empty, or contains non-string/empty items.
        EmbeddingServiceError: If model loading or inference fails.
    """
    if not isinstance(texts, list):
        raise EmbeddingValidationError(f"Expected texts to be a list, got {type(texts).__name__}.")

    if len(texts) == 0:
        raise EmbeddingValidationError("Input texts list cannot be empty.")

    cleaned_texts: list[str] = []
    for idx, item in enumerate(texts):
        if not isinstance(item, str):
            raise EmbeddingValidationError(
                f"Item at index {idx} must be a string, got {type(item).__name__}."
            )
        stripped = item.strip()
        if not stripped:
            raise EmbeddingValidationError(
                f"Item at index {idx} cannot be empty or whitespace-only."
            )
        cleaned_texts.append(stripped)

    model = get_embedding_model(model_name=model_name, device=device)

    try:
        embeddings = model.encode(
            cleaned_texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if hasattr(embeddings, "tolist"):
            raw_list = embeddings.tolist()
            return [[float(val) for val in vec] for vec in raw_list]
        return [[float(val) for val in vec] for vec in embeddings]
    except Exception as exc:
        logger.error("Failed to generate embeddings for %d texts: %s", len(cleaned_texts), exc)
        raise EmbeddingServiceError(f"Batch embedding inference failed: {exc}") from exc


def unload_embedding_model() -> None:
    """Reset the cached embedding model to free memory if needed."""
    global _cached_model, _cached_model_name, _cached_device
    with _model_lock:
        _cached_model = None
        _cached_model_name = None
        _cached_device = None
        logger.info("Embedding model cache cleared.")
