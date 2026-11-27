import asyncio
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm_service import (
    LLMServiceError,
    generate_ollama_chat_completion,
    parse_and_validate_analysis_json,
)
from app.ai.nlp_service import process_meeting_transcript_nlp
from app.ai.prompts import build_meeting_analysis_prompt
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.meeting import Meeting
from app.models.meeting_analysis import MeetingAnalysis
from app.models.transcript import MeetingTranscript
from app.services.meeting_analysis_service import (
    initialize_meeting_analysis,
    internal_mark_analysis_failed,
    internal_persist_analysis_results,
    internal_update_analysis_status,
)
from app.services.meeting_service import get_user_meeting

logger = logging.getLogger(__name__)


def start_meeting_analysis_job(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> MeetingAnalysis:
    """Validate ownership, transcript availability, and transition analysis to processing.

    Uses row locking via initialize_meeting_analysis() to serialize request states.
    Prevents duplicate runs if analysis is currently 'processing'.
    """
    meeting = get_user_meeting(db, meeting_id, user_id)

    # 1. Verify transcript exists and is not empty
    transcript = db.scalar(
        select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.id)
    )
    if transcript is None or not transcript.full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot analyze meeting: transcript is not available or is empty.",
        )

    # 2. Check current analysis status under lock
    current_analysis = db.scalar(
        select(MeetingAnalysis)
        .where(MeetingAnalysis.meeting_id == meeting.id)
        .with_for_update()
    )
    if current_analysis is not None and current_analysis.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already in progress for this meeting.",
        )

    # 3. Initialize/reset record to 'pending', then move to 'processing'
    analysis = initialize_meeting_analysis(db, meeting_id, user_id)
    analysis.status = "processing"
    db.commit()
    db.refresh(analysis)
    return analysis


async def _async_run_analysis_pipeline(meeting_id: int) -> None:
    """Async core of the pipeline: DB reads, NLP, Ollama async call, and DB write."""
    db = SessionLocal()
    try:
        meeting = db.scalar(select(Meeting).where(Meeting.id == meeting_id))
        if meeting is None:
            logger.warning("Analysis task: meeting ID=%d not found", meeting_id)
            return

        transcript = db.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting_id)
        )
        if transcript is None or not transcript.full_text.strip():
            internal_mark_analysis_failed(
                db, meeting_id, "Transcript is missing or empty."
            )
            return

        # 1. Traditional NLP Processing (CPU-bound, fast)
        logger.info("Starting traditional NLP extraction for meeting ID=%d...", meeting_id)
        nlp_result = process_meeting_transcript_nlp(
            full_text=transcript.full_text,
            segments=transcript.segments or [],
        )
        logger.info(
            "NLP extraction completed for meeting ID=%d: %d entities, %d keywords.",
            meeting_id,
            len(nlp_result.entities),
            len(nlp_result.keywords),
        )

        # 2. Build safe prompt
        system_prompt, user_prompt = build_meeting_analysis_prompt(
            meeting_title=meeting.title,
            full_text=transcript.full_text,
            segments=transcript.segments or [],
            nlp_result=nlp_result,
        )

        # 3. Call local Ollama
        logger.info(
            "Sending analysis prompt to Ollama (model='%s') for meeting ID=%d...",
            settings.OLLAMA_MODEL,
            meeting_id,
        )
        raw_llm_output = await generate_ollama_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # 4. Parse & validate with Pydantic
        logger.info("Validating structured LLM response for meeting ID=%d...", meeting_id)
        validated_data = parse_and_validate_analysis_json(raw_llm_output)

        # 5. Persist results
        internal_persist_analysis_results(
            db=db,
            meeting_id=meeting_id,
            summary=validated_data["summary"],
            key_points=validated_data["key_points"],
            decisions=validated_data["decisions"],
            action_items=validated_data["action_items"],
            deadlines=validated_data["deadlines"],
            unresolved_questions=validated_data["unresolved_questions"],
            analysis_provider="ollama",
            model_name=settings.OLLAMA_MODEL,
        )
        logger.info("Meeting analysis successfully completed and saved for meeting ID=%d.", meeting_id)

    except LLMServiceError as exc:
        logger.error("LLM Service failure for meeting ID=%d: %s", meeting_id, exc)
        internal_mark_analysis_failed(db, meeting_id, str(exc))
    except Exception as exc:
        logger.error("Unexpected error analyzing meeting ID=%d: %s", meeting_id, exc, exc_info=True)
        internal_mark_analysis_failed(
            db, meeting_id, "An unexpected error occurred during meeting analysis."
        )
    finally:
        db.close()


def process_meeting_analysis_task(meeting_id: int) -> None:
    """Sync entry point for FastAPI BackgroundTasks executing the async pipeline."""
    logger.info("Background analysis task triggered for meeting ID=%d", meeting_id)
    try:
        asyncio.run(_async_run_analysis_pipeline(meeting_id))
    except Exception as exc:
        logger.error("Background runner exception for meeting ID=%d: %s", meeting_id, exc, exc_info=True)
