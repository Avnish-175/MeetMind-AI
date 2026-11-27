from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TranscriptSegment(BaseModel):
    """A single timestamped segment of a meeting transcript."""

    id: int
    start: float
    end: float
    text: str


class MeetingTranscriptResponse(BaseModel):
    """API response schema for a meeting's full transcript and segments."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    full_text: str
    language: str | None
    language_probability: float | None
    duration_seconds: float | None
    model_name: str
    segments: list[TranscriptSegment]
    created_at: datetime
    updated_at: datetime
