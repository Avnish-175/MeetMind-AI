import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.embedding_service import EmbeddingServiceError, generate_embedding
from app.ai.llm_service import (
    LLMServiceError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    generate_chat_response,
)
from app.ai.prompts import RAG_CHAT_SYSTEM_PROMPT, build_rag_context_prompt
from app.core.config import settings
from app.models.meeting import Meeting
from app.services.vector_store_service import VectorStoreError, search_similar_embeddings

logger = logging.getLogger(__name__)


async def answer_meeting_question(
    db: Session,
    user_id: int,
    question: str,
    meeting_id: int | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    top_k: int | None = None,
    min_similarity: float | None = None,
) -> dict[str, Any]:
    """Retrieve relevant meeting transcript chunks for `user_id` and generate a grounded answer."""
    if meeting_id is not None:
        meeting = (
            db.query(Meeting)
            .filter(Meeting.id == meeting_id, Meeting.user_id == user_id)
            .first()
        )
        if meeting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected meeting not found.",
            )

    resolved_top_k = int(top_k if top_k is not None else settings.RAG_TOP_K)
    resolved_min_sim = float(
        min_similarity if min_similarity is not None else settings.RAG_MIN_SIMILARITY
    )

    try:
        query_vector = generate_embedding(question)
    except EmbeddingServiceError as exc:
        logger.error("Failed to generate query embedding for user %d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local embedding service unavailable: {exc}",
        )

    try:
        raw_results = search_similar_embeddings(
            db=db,
            query_embedding=query_vector,
            user_id=user_id,
            top_k=resolved_top_k,
            meeting_id=meeting_id,
        )
    except VectorStoreError as exc:
        logger.error("Vector search failed for user %d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search meeting embeddings: {exc}",
        )

    filtered_results = [
        item for item in raw_results if item["similarity_score"] >= resolved_min_sim
    ]

    if not filtered_results:
        scope_desc = (
            "the selected meeting"
            if meeting_id is not None
            else "your indexed meetings"
        )
        return {
            "answer": (
                f"I could not find relevant information in {scope_desc} to answer your question. "
                "Please make sure the meeting has been transcribed and indexed for AI search."
            ),
            "citations": [],
        }

    # Fetch meeting titles for all retrieved chunks (enforcing user_id ownership)
    retrieved_meeting_ids = list({item["meeting_id"] for item in filtered_results})
    meetings = (
        db.query(Meeting.id, Meeting.title)
        .filter(Meeting.id.in_(retrieved_meeting_ids), Meeting.user_id == user_id)
        .all()
    )
    title_map = {m.id: m.title for m in meetings}

    enriched_chunks: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    for item in filtered_results:
        meta = item.get("metadata") or {}
        m_id = item["meeting_id"]
        m_title = title_map.get(m_id, f"Meeting #{m_id}")
        start_time = meta.get("start_time")
        end_time = meta.get("end_time")
        segment_ids = meta.get("segment_ids") or []
        content = item["content"]

        enriched_chunks.append(
            {
                "meeting_id": m_id,
                "meeting_title": m_title,
                "start_time": start_time,
                "end_time": end_time,
                "segment_ids": segment_ids,
                "content": content,
            }
        )

        excerpt = content[:260].strip()
        if len(content) > 260:
            excerpt += "..."

        citations.append(
            {
                "meeting_id": m_id,
                "meeting_title": m_title,
                "chunk_index": item["chunk_index"],
                "start_time": start_time,
                "end_time": end_time,
                "segment_ids": segment_ids,
                "excerpt": excerpt,
                "similarity_score": round(float(item["similarity_score"]), 4),
            }
        )

    rag_user_prompt = build_rag_context_prompt(
        question=question,
        retrieved_chunks=enriched_chunks,
    )

    # Include recent prior conversation turns (excluding the current question which is in rag_user_prompt)
    llm_messages: list[dict[str, str]] = []
    if conversation_history:
        prior = conversation_history[:-1] if len(conversation_history) > 1 else []
        llm_messages.extend(prior[-6:])
    llm_messages.append({"role": "user", "content": rag_user_prompt})

    try:
        answer_text = await generate_chat_response(
            messages=llm_messages,
            system_prompt=RAG_CHAT_SYSTEM_PROMPT,
        )
    except (OllamaConnectionError, OllamaModelNotFoundError, LLMServiceError, Exception) as exc:
        logger.error("RAG LLM generation failed for user %d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local AI model generation failed: {exc}. Your message was saved.",
        )

    return {
        "answer": answer_text,
        "citations": citations,
    }
