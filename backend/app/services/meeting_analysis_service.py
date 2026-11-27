import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.meeting_analysis import MeetingAnalysis
from app.services.meeting_service import get_user_meeting

logger = logging.getLogger(__name__)


def get_meeting_analysis(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> MeetingAnalysis:
    """Retrieve the analysis record for a meeting owned by the given user.

    Raises HTTP 404 if the meeting does not exist, is not owned by the user,
    or has no analysis record yet.
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
    """Initialize or reset an analysis record for a user's meeting in 'pending' status."""
    meeting = get_user_meeting(db, meeting_id, user_id)

    analysis = db.scalar(
        select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting.id)
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
        )
        db.add(analysis)
    else:
        analysis.status = "pending"
        analysis.error_message = None

    try:
        db.commit()
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
    status_value: str,
    error_message: str | None = None,
) -> MeetingAnalysis | None:
    """Update status and optional error message for a meeting's analysis."""
    analysis = db.scalar(
        select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting_id)
    )
    if analysis is None:
        return None

    analysis.status = status_value
    if error_message is not None:
        analysis.error_message = error_message[:2000]
    elif status_value == "completed":
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
            status_value,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update analysis status.",
        ) from exc


def persist_analysis_results(
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
    """Persist structured analysis insights and mark the record as completed."""
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


def mark_analysis_failed(
    db: Session,
    meeting_id: int,
    error_message: str,
) -> None:
    """Mark an analysis record as failed with a safe error message."""
    try:
        analysis = db.scalar(
            select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == meeting_id)
        )
        if analysis is None:
            analysis = MeetingAnalysis(
                meeting_id=meeting_id,
                status="failed",
                error_message=error_message[:2000],
            )
            db.add(analysis)
        else:
            analysis.status = "failed"
            analysis.error_message = error_message[:2000]

        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Failed to mark analysis as failed for meeting ID=%d: %s",
            meeting_id,
            exc,
            exc_info=True,
        )
