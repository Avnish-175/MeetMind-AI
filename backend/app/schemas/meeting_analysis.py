from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnalysisStatus = Literal["pending", "processing", "completed", "failed"]


class KeyPointItem(BaseModel):
    """Structured key point or highlight extracted from meeting discussions."""

    text: str
    transcript_segment_ids: list[int] = Field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None


class DecisionItem(BaseModel):
    """A clear decision or conclusion reached during the meeting."""

    text: str
    rationale: str | None = None
    responsible_person: str | None = None
    transcript_segment_ids: list[int] = Field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None


class ActionItem(BaseModel):
    """An action item assigned to an owner with optional due date."""

    text: str
    responsible_person: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high"] | None = None
    transcript_segment_ids: list[int] = Field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None


class DeadlineItem(BaseModel):
    """A milestone, target date, or time-sensitive commitment discussed in the meeting."""

    text: str
    due_date: str | None = None
    responsible_person: str | None = None
    transcript_segment_ids: list[int] = Field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None


class UnresolvedQuestionItem(BaseModel):
    """An open question or topic that was raised but left unresolved."""

    text: str
    raised_by: str | None = None
    transcript_segment_ids: list[int] = Field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None


class MeetingAnalysisResponse(BaseModel):
    """API response schema for meeting analysis and extracted insights."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    status: str
    summary: str | None = None
    key_points: list[KeyPointItem] = Field(default_factory=list)
    decisions: list[DecisionItem] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    deadlines: list[DeadlineItem] = Field(default_factory=list)
    unresolved_questions: list[UnresolvedQuestionItem] = Field(default_factory=list)
    error_message: str | None = None
    analysis_provider: str | None = None
    model_name: str | None = None
    created_at: datetime
    updated_at: datetime
