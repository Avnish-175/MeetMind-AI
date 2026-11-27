from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AnalysisStatus = Literal["pending", "processing", "completed", "failed"]


class BaseInsightItem(BaseModel):
    """Base schema for structured meeting insight items with segment and time validation."""

    text: str = Field(..., min_length=1)
    transcript_segment_ids: list[int] = Field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None

    @field_validator("text")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Insight text must not be empty.")
        return stripped

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_non_negative_time(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Timestamp must not be negative.")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "BaseInsightItem":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time < self.start_time
        ):
            raise ValueError("end_time cannot be earlier than start_time.")
        return self


class KeyPointItem(BaseInsightItem):
    """Structured key point or highlight extracted from meeting discussions."""

    pass


class DecisionItem(BaseInsightItem):
    """A clear decision or conclusion reached during the meeting."""

    rationale: str | None = None
    responsible_person: str | None = None


class ActionItem(BaseInsightItem):
    """An action item assigned to an owner with optional due date."""

    responsible_person: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high"] | None = None


class DeadlineItem(BaseInsightItem):
    """A milestone, target date, or time-sensitive commitment discussed in the meeting."""

    due_date: str | None = None
    responsible_person: str | None = None


class UnresolvedQuestionItem(BaseInsightItem):
    """An open question or topic that was raised but left unresolved."""

    raised_by: str | None = None


class MeetingAnalysisResponse(BaseModel):
    """API response schema for meeting analysis and extracted insights."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    status: AnalysisStatus
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
