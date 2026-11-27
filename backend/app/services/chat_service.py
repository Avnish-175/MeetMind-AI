import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.ai.llm_service import (
    LLMServiceError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    generate_chat_response,
)
from app.ai.prompts import DEFAULT_CHAT_SYSTEM_PROMPT
from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.models.meeting import Meeting
from app.schemas.chat import ConversationCreate
from app.services.rag_service import answer_meeting_question

logger = logging.getLogger(__name__)


def create_conversation(
    db: Session,
    user_id: int,
    payload: ConversationCreate | None = None,
) -> Conversation:
    """Create a new chat conversation for the authenticated user."""
    title = (payload.title if payload and payload.title else "New Conversation").strip()
    if not title:
        title = "New Conversation"

    conversation = Conversation(
        user_id=user_id,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    logger.info("Created conversation %d for user %d", conversation.id, user_id)
    return conversation


def list_user_conversations(
    db: Session,
    user_id: int,
) -> list[Conversation]:
    """List all conversations belonging to the authenticated user ordered by most recently updated."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .all()
    )


def get_user_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> Conversation | None:
    """Retrieve a single conversation ensuring user ownership."""
    return (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )


def get_user_conversation_detail(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> Conversation | None:
    """Retrieve conversation details with its messages eager-loaded, ensuring user ownership."""
    return (
        db.query(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )


def update_conversation_title(
    db: Session,
    conversation_id: int,
    user_id: int,
    new_title: str,
) -> Conversation:
    """Update a conversation title ensuring user ownership."""
    conversation = get_user_conversation(db, conversation_id, user_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    stripped_title = new_title.strip()
    if not stripped_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conversation title cannot be empty.",
        )

    conversation.title = stripped_title
    conversation.updated_at = func.now()
    db.commit()
    db.refresh(conversation)
    logger.info("Updated title for conversation %d to '%s'", conversation_id, stripped_title)
    return conversation


def delete_user_conversation(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> None:
    """Delete a conversation and all its messages, ensuring user ownership."""
    conversation = get_user_conversation(db, conversation_id, user_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    db.delete(conversation)
    db.commit()
    logger.info("Deleted conversation %d for user %d", conversation_id, user_id)


async def send_user_message_and_generate_response(
    db: Session,
    conversation_id: int,
    user_id: int,
    content: str,
    mode: str = "general",
    meeting_id: int | None = None,
) -> ChatMessage:
    """Persist the user message, generate a general or meeting-RAG response, and persist it.

    If model generation fails, the user message remains safely persisted in the database.
    """
    if mode not in ("general", "meeting"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid chat mode. Must be 'general' or 'meeting'.",
        )

    # 1. Validate conversation ownership
    conversation = get_user_conversation(db, conversation_id, user_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    resolved_meeting_id = meeting_id if mode == "meeting" else None
    if mode == "meeting" and resolved_meeting_id is not None:
        meeting = (
            db.query(Meeting)
            .filter(Meeting.id == resolved_meeting_id, Meeting.user_id == user_id)
            .first()
        )
        if meeting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected meeting not found.",
            )

    clean_content = content.strip()
    if not clean_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be blank.",
        )

    # 2. Persist the user message first
    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=clean_content,
        mode=mode,
        meeting_id=resolved_meeting_id,
    )

    # Auto-title conversation if it still has the default title
    if conversation.title in ("New Conversation", "New Chat", ""):
        first_line = clean_content.split("\n")[0].strip()
        if len(first_line) > 50:
            first_line = first_line[:47] + "..."
        if first_line:
            conversation.title = first_line

    conversation.updated_at = func.now()
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    logger.info(
        "Persisted user message %d in conversation %d (mode=%s)",
        user_message.id,
        conversation.id,
        mode,
    )

    # 3. Retrieve conversation message history
    history_records = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    context_messages: list[dict[str, str]] = [
        {"role": rec.role, "content": rec.content} for rec in history_records
    ]

    # 4 & 5. Generate assistant response according to mode
    citations_data: list[dict[str, Any]] | None = None
    if mode == "meeting":
        rag_result = await answer_meeting_question(
            db=db,
            user_id=user_id,
            question=clean_content,
            meeting_id=resolved_meeting_id,
            conversation_history=context_messages,
        )
        assistant_content = rag_result["answer"]
        citations_data = rag_result.get("citations") or None
    else:
        try:
            assistant_content = await generate_chat_response(
                messages=context_messages,
                system_prompt=DEFAULT_CHAT_SYSTEM_PROMPT,
            )
        except (OllamaConnectionError, OllamaModelNotFoundError, LLMServiceError, Exception) as exc:
            logger.error(
                "Local AI chat generation failed for conversation %d: %s",
                conversation.id,
                exc,
            )
            # The user message was already committed in step 2 and is not lost.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Local AI model generation failed: {exc}. Your message was saved.",
            )

    # 6. Persist the assistant response
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
        mode=mode,
        meeting_id=resolved_meeting_id,
        citations=citations_data,
    )
    conversation.updated_at = func.now()
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    logger.info(
        "Persisted assistant response %d in conversation %d (mode=%s)",
        assistant_message.id,
        conversation.id,
        mode,
    )

    # 7. Return saved assistant message
    return assistant_message
