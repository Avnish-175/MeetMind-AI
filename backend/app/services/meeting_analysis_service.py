import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.meeting_analysis import MeetingAnalysis
from app.services.meeting_service import get_user_meeting

logger = logging.getLogger(__name__)

ALLOWED_ANALYSIS_STATUSES: set[str] = {"pending", "processing", "completed", "failed"}
MAX_ERROR_MESSAGE_LENGTH = 2000


def _validate_status_value(status_value: str) -> str:
    """Ensure analysis status belongs to the predefined allowed set."""
    normalized = status_value.strip().lower()
    if normalized not in ALLOWED_ANALYSIS_STATUSES:
        raise ValueError(f"Invalid analysis status: {status_value}")
    return normalized


# ============================================================================
# USER-FACING FUNCTIONS (MANDATORY user_id AND OWNERSHIP VALIDATION)
# ============================================================================

def get_meeting_analysis(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> MeetingAnalysis:
    """Retrieve the analysis record for a meeting owned by the given user.

    Validates meeting ownership via get_user_meeting(). Raises HTTP 404 if the
    meeting does not exist, is unowned, or has no analysis record yet.
    """
    meeting = get_user_meeting(db, meeting_id, user_id)
    analysis = db.scalar(
        select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting.id)
    )
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found for this meeting.",
        )
    return analysis


def initialize_meeting_analysis(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> MeetingAnalysis:
    """Initialize or reinitialize an analysis record for a user's meeting in 'pending' status.

    Uses a row-level lock on the meeting row (SELECT FOR UPDATE) to serialize
    initialization and avoid race conditions or duplicate inserts. When an existing
    analysis is reinitialized, all stale results (summary, key_points, decisions,
    action_items, deadlines, unresolved_questions, error_message, analysis_provider,
    model_name) are cleared and the status is reset to 'pending'.
    """
    # 1. Lock meeting row and verify ownership
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id, Meeting.user_id == user_id)
        .with_for_update()
    )
    meeting = db.scalar(stmt)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found.",
        )

    # 2. Check for existing analysis record under lock
    analysis = db.scalar(
        select(MeetingAnalysis)
        .where(MeetingAnalysis.meeting_id == meeting.id)
        .with_for_update()
    )

    if analysis is None:
        analysis = MeetingAnalysis(
            meeting_id=meeting.id,
            status="pending",
            summary=None,
            key_points=[],
            decisions=[],
            action_items=[],
            deadlines=[],
            unresolved_questions=[],
            error_message=None,
            analysis_provider=None,
            model_name=None,
        )
        db.add(analysis)
    else:
        # Clear all stale analysis results and reset to pending
        analysis.status = "pending"
        analysis.summary = None
        analysis.key_points = []
        analysis.decisions = []
        analysis.action_items = []
        analysis.deadlines = []
        analysis.unresolved_questions = []
        analysis.error_message = None
        analysis.analysis_provider = None
        analysis.model_name = None

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning(
            "Integrity conflict during meeting analysis initialization for meeting ID=%d: %s",
            meeting_id,
            exc,
        )
        analysis = db.scalar(
            select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting.id)
        )
        if analysis is not None:
            return analysis
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting analysis initialization conflict occurred.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Failed to initialize meeting analysis for meeting ID=%d: %s",
            meeting_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize meeting analysis record.",
        ) from exc

    db.refresh(analysis)
    return analysis


def update_analysis_status(
    db: Session,
    meeting_id: int,
    user_id: int,
    status_value: str,
    error_message: str | None = None,
) -> MeetingAnalysis | None:
    """User-facing update of status and optional error message for a meeting's analysis.

    Validates meeting ownership via get_user_meeting() before modifying the record.
    """
    get_user_meeting(db, meeting_id, user_id)
    return internal_update_analysis_status(
        db=db,
        meeting_id=meeting_id,
        status_value=status_value,
        error_message=error_message,
    )


def persist_analysis_results(
    db: Session,
    meeting_id: int,
    user_id: int,
    summary: str | None,
    key_points: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
    deadlines: list[dict[str, Any]],
    unresolved_questions: list[dict[str, Any]],
    analysis_provider: str | None = None,
    model_name: str | None = None,
) -> MeetingAnalysis:
    """User-facing persistence of structured analysis insights with mandatory ownership check."""
    get_user_meeting(db, meeting_id, user_id)
    return internal_persist_analysis_results(
        db=db,
        meeting_id=meeting_id,
        summary=summary,
        key_points=key_points,
        decisions=decisions,
        action_items=action_items,
        deadlines=deadlines,
        unresolved_questions=unresolved_questions,
        analysis_provider=analysis_provider,
        model_name=model_name,
    )


def mark_analysis_failed(
    db: Session,
    meeting_id: int,
    user_id: int,
    error_message: str,
) -> None:
    """User-facing mark of analysis as failed with mandatory ownership check."""
    get_user_meeting(db, meeting_id, user_id)
    internal_mark_analysis_failed(
        db=db,
        meeting_id=meeting_id,
        error_message=error_message,
    )


# ============================================================================
# INTERNAL / BACKGROUND-TASK HELPER FUNCTIONS (TRUSTED PRE-AUTHORIZED WORKERS)
# ============================================================================

def internal_update_analysis_status(
    db: Session,
    meeting_id: int,
    status_value: str,
    error_message: str | None = None,
) -> MeetingAnalysis | None:
    """INTERNAL ONLY: Update status and optional error message for a meeting's analysis.

    RESTRICTION: This function does NOT perform user ownership checks and MUST ONLY be called
    by trusted asynchronous background workers with an isolated session on pre-validated IDs.
    """
    try:
        valid_status = _validate_status_value(status_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    analysis = db.scalar(
        select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting_id)
    )
    if analysis is None:
        return None

    analysis.status = valid_status
    if error_message is not None:
        analysis.error_message = error_message[:MAX_ERROR_MESSAGE_LENGTH]
    elif valid_status == "completed":
        analysis.error_message = None

    try:
        db.commit()
        db.refresh(analysis)
        return analysis
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Failed to update analysis status for meeting ID=%d to '%s': %s",
            meeting_id,
            valid_status,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update analysis status.",
        ) from exc


def internal_persist_analysis_results(
    db: Session,
    meeting_id: int,
    summary: str | None,
    key_points: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
    deadlines: list[dict[str, Any]],
    unresolved_questions: list[dict[str, Any]],
    analysis_provider: str | None = None,
    model_name: str | None = None,
) -> MeetingAnalysis:
    """INTERNAL ONLY: Persist structured analysis insights and mark record as completed.

    RESTRICTION: This function does NOT perform user ownership checks and MUST ONLY be called
    by trusted asynchronous background workers with an isolated session on pre-validated IDs.
    """
    analysis = db.scalar(
        select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting_id)
    )
    if analysis is None:
        analysis = MeetingAnalysis(
            meeting_id=meeting_id,
            status="completed",
            summary=summary,
            key_points=key_points,
            decisions=decisions,
            action_items=action_items,
            deadlines=deadlines,
            unresolved_questions=unresolved_questions,
            analysis_provider=analysis_provider,
            model_name=model_name,
            error_message=None,
        )
        db.add(analysis)
    else:
        analysis.status = "completed"
        analysis.summary = summary
        analysis.key_points = key_points
        analysis.decisions = decisions
        analysis.action_items = action_items
        analysis.deadlines = deadlines
        analysis.unresolved_questions = unresolved_questions
        analysis.analysis_provider = analysis_provider
        analysis.model_name = model_name
        analysis.error_message = None

    try:
        db.commit()
        db.refresh(analysis)
        return analysis
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Failed to persist analysis results for meeting ID=%d: %s",
            meeting_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save meeting analysis results.",
        ) from exc


def internal_mark_analysis_failed(
    db: Session,
    meeting_id: int,
    error_message: str,
) -> None:
    """INTERNAL ONLY: Mark an analysis record as failed with a safe, length-limited error message.

    RESTRICTION: This function does NOT perform user ownership checks and MUST ONLY be called
    by trusted asynchronous background workers with an isolated session on pre-validated IDs.
    """
    truncated_error = error_message[:MAX_ERROR_MESSAGE_LENGTH]
    try:
        analysis = db.scalar(
            select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting_id)
        )
        if analysis is None:
            analysis = MeetingAnalysis(
                meeting_id=meeting_id,
                status="failed",
                error_message=truncated_error,
            )
            db.add(analysis)
        else:
            analysis.status = "failed"
            analysis.error_message = truncated_error

        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Failed to mark analysis as failed for meeting ID=%d: %s",
            meeting_id,
            exc,
            exc_info=True,
        )
