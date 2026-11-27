from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MeetingCreateMetadata(BaseModel):
    """Validated metadata for creating a new meeting."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Meeting title must not be empty.")
        return stripped

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None


class MeetingResponse(BaseModel):
    """Safe meeting representation returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str | None
    media_type: Literal["audio", "video"]
    original_filename: str
    mime_type: str
    file_size_bytes: int
    duration_seconds: float | None
    processing_status: str
    processing_error: str | None = None
    created_at: datetime
    updated_at: datetime


class MeetingListResponse(BaseModel):
    """Paginated/structured list of meetings belonging to the authenticated user."""

    items: list[MeetingResponse]
    total: int


class TranscriptionStartResponse(BaseModel):
    """Response returned when a meeting transcription job is accepted."""

    meeting_id: int
    processing_status: str
    message: str
