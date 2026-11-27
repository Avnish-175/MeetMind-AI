from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CitationItem(BaseModel):
    """Structured source citation returned for meeting-aware RAG responses."""

    meeting_id: int
    meeting_title: str
    chunk_index: int
    start_time: float | None = None
    end_time: float | None = None
    segment_ids: list[int] = []
    excerpt: str
    similarity_score: float


class ChatMessageCreate(BaseModel):
    """Schema for sending a new message in a conversation."""

    content: str = Field(..., min_length=1)
    mode: Literal["general", "meeting"] = "general"
    meeting_id: int | None = Field(default=None, gt=0)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message content cannot be blank.")
        return stripped


class ChatMessageResponse(BaseModel):
    """Schema representing a stored chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    mode: str = "general"
    meeting_id: int | None = None
    citations: list[CitationItem] | None = None
    created_at: datetime


class ConversationCreate(BaseModel):
    """Schema for creating a new chat conversation."""

    title: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation's title."""

    title: str = Field(..., min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Conversation title cannot be blank.")
        return stripped


class ConversationResponse(BaseModel):
    """Summary schema for a chat conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    """Detailed schema for a chat conversation including its ordered messages."""

    messages: list[ChatMessageResponse] = []


class ConversationListResponse(BaseModel):
    """Paginated/structured list of conversations belonging to the authenticated user."""

    items: list[ConversationResponse]
    total: int
