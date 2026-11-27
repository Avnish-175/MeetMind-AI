import asyncio
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.llm_service import (
    LLMServiceError,
    generate_ollama_chat_completion,
    parse_and_validate_analysis_json,
    parse_summary_synthesis_json,
)
from app.ai.nlp_service import process_meeting_transcript_nlp
from app.ai.prompts import (
    build_meeting_analysis_prompt,
    build_summary_synthesis_prompt,
    chunk_transcript_segments,
)
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.meeting import Meeting
from app.models.meeting_analysis import MeetingAnalysis
from app.models.transcript import MeetingTranscript
from app.services.meeting_analysis_service import (
    internal_mark_analysis_failed,
    internal_persist_analysis_results,
)

logger = logging.getLogger(__name__)


def start_meeting_analysis_job(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> MeetingAnalysis:
    """Lock the meeting row, verify ownership & transcript, and atomically mark analysis processing."""
    meeting = db.scalar(
        select(Meeting)
        .where(Meeting.id == meeting_id, Meeting.user_id == user_id)
        .with_for_update()
    )
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found.",
        )

    transcript = db.scalar(
        select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.id)
    )
    if transcript is None or not transcript.full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot analyze meeting: transcript is not available or is empty.",
        )

    analysis = db.scalar(
        select(MeetingAnalysis)
        .where(MeetingAnalysis.meeting_id == meeting.id)
        .with_for_update()
    )
    if analysis is not None and analysis.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already in progress for this meeting.",
        )

    if analysis is None:
        analysis = MeetingAnalysis(
            meeting_id=meeting.id,
            status="processing",
            summary=None,
            key_points=[],
            decisions=[],
            action_items=[],
            deadlines=[],
            unresolved_questions=[],
            nlp_insights=None,
            error_message=None,
            analysis_provider=None,
            model_name=None,
        )
        db.add(analysis)
    else:
        analysis.status = "processing"
        analysis.summary = None
        analysis.key_points = []
        analysis.decisions = []
        analysis.action_items = []
        analysis.deadlines = []
        analysis.unresolved_questions = []
        analysis.nlp_insights = None
        analysis.error_message = None
        analysis.analysis_provider = None
        analysis.model_name = None

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already being initialized for this meeting.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Failed to start meeting analysis for meeting ID=%d: %s",
            meeting_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start meeting analysis.",
        ) from exc

    db.refresh(analysis)
    return analysis


async def _async_run_analysis_pipeline(meeting_id: int) -> None:
    """Async core of the pipeline: DB reads, NLP, chunked Ollama calls, validation, and DB write."""
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

        segments = transcript.segments or []

        logger.info("Starting traditional NLP extraction for meeting ID=%d...", meeting_id)
        nlp_result = process_meeting_transcript_nlp(
            full_text=transcript.full_text,
            segments=segments,
        )
        logger.info(
            "NLP extraction completed for meeting ID=%d: %d entities, %d keywords.",
            meeting_id,
            len(nlp_result.entities),
            len(nlp_result.keywords),
        )

        chunks = chunk_transcript_segments(segments) if segments else [[]]
        total_chunks = len(chunks)

        merged_key_points = []
        merged_decisions = []
        merged_action_items = []
        merged_deadlines = []
        merged_unresolved_questions = []
        chunk_summaries: list[str] = []

        for idx, chunk in enumerate(chunks, start=1):
            system_prompt, user_prompt = build_meeting_analysis_prompt(
                meeting_title=meeting.title,
                full_text=transcript.full_text,
                segments=chunk,
                nlp_result=nlp_result,
                chunk_index=idx,
                total_chunks=total_chunks,
            )

            logger.info(
                "Sending analysis prompt chunk %d/%d to Ollama (model='%s') for meeting ID=%d...",
                idx,
                total_chunks,
                settings.OLLAMA_MODEL,
                meeting_id,
            )
            raw_llm_output = await generate_ollama_chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            validated_chunk = parse_and_validate_analysis_json(
                raw_llm_output,
                segments=chunk,
            )
            if validated_chunk["summary"]:
                chunk_summaries.append(validated_chunk["summary"])
            merged_key_points.extend(validated_chunk["key_points"])
            merged_decisions.extend(validated_chunk["decisions"])
            merged_action_items.extend(validated_chunk["action_items"])
            merged_deadlines.extend(validated_chunk["deadlines"])
            merged_unresolved_questions.extend(validated_chunk["unresolved_questions"])

        if len(chunk_summaries) > 1:
            synth_sys, synth_usr = build_summary_synthesis_prompt(
                meeting_title=meeting.title,
                chunk_summaries=chunk_summaries,
            )
            raw_synth = await generate_ollama_chat_completion(
                system_prompt=synth_sys,
                user_prompt=synth_usr,
            )
            final_summary = parse_summary_synthesis_json(raw_synth)
        else:
            final_summary = chunk_summaries[0] if chunk_summaries else None

        internal_persist_analysis_results(
            db=db,
            meeting_id=meeting_id,
            summary=final_summary,
            key_points=merged_key_points,
            decisions=merged_decisions,
            action_items=merged_action_items,
            deadlines=merged_deadlines,
            unresolved_questions=merged_unresolved_questions,
            nlp_insights=nlp_result.model_dump(),
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
