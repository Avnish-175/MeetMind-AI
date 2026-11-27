from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.meeting import Meeting
from app.models.transcript import MeetingTranscript
from app.schemas.meeting import MeetingCreateMetadata
from app.services.media_service import MediaProcessingError, extract_normalized_audio
from app.services.storage_service import delete_stored_file, save_upload_file
from app.services.transcription_service import TranscriptionError, transcribe_audio


async def create_meeting(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    upload_file: UploadFile,
) -> Meeting:
    """Validate metadata, store uploaded media, and persist a new Meeting record."""
    try:
        metadata = MeetingCreateMetadata(title=title, description=description)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors()[0]["msg"],
        ) from exc

    stored_file = await save_upload_file(upload_file)

    meeting = Meeting(
        user_id=user_id,
        title=metadata.title,
        description=metadata.description,
        media_type=stored_file.media_type,
        original_filename=stored_file.original_filename,
        storage_path=stored_file.storage_path,
        mime_type=stored_file.mime_type,
        file_size_bytes=stored_file.file_size_bytes,
        duration_seconds=None,
        processing_status="uploaded",
    )

    db.add(meeting)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        delete_stored_file(stored_file.storage_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save meeting record.",
        ) from exc

    db.refresh(meeting)
    return meeting


def list_user_meetings(db: Session, user_id: int) -> list[Meeting]:
    """Return all meetings owned by the given user, newest first."""
    stmt = (
        select(Meeting)
        .where(Meeting.user_id == user_id)
        .order_by(Meeting.created_at.desc(), Meeting.id.desc())
    )
    return list(db.scalars(stmt).all())


def get_user_meeting(db: Session, meeting_id: int, user_id: int) -> Meeting:
    """Retrieve a single meeting owned by the given user or raise 404."""
    stmt = select(Meeting).where(
        Meeting.id == meeting_id,
        Meeting.user_id == user_id,
    )
    meeting = db.scalar(stmt)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found.",
        )
    return meeting


def delete_user_meeting(db: Session, meeting_id: int, user_id: int) -> None:
    """Delete a user's meeting record and remove its associated media file."""
    meeting = get_user_meeting(db, meeting_id, user_id)
    storage_path = meeting.storage_path

    db.delete(meeting)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete meeting.",
        ) from exc

    delete_stored_file(storage_path)


def start_meeting_transcription(db: Session, meeting_id: int, user_id: int) -> Meeting:
    """Validate ownership and state with a row lock, then mark a meeting as processing."""
    stmt = (
        select(Meeting)
        .where(
            Meeting.id == meeting_id,
            Meeting.user_id == user_id,
        )
        .with_for_update()
    )
    meeting = db.scalar(stmt)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found.",
        )

    if meeting.processing_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transcription is already in progress for this meeting.",
        )

    if meeting.processing_status == "transcribed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This meeting has already been transcribed.",
        )

    meeting.processing_status = "processing"
    meeting.processing_error = None

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update meeting processing status.",
        ) from exc

    db.refresh(meeting)
    return meeting


def _mark_transcription_failed(db: Session, meeting_id: int, error_message: str) -> None:
    """Persist a failed processing status and safe error message in the background."""
    try:
        meeting = db.scalar(select(Meeting).where(Meeting.id == meeting_id))
        if meeting is None:
            return
        meeting.processing_status = "failed"
        meeting.processing_error = error_message[:2000]
        db.commit()
    except SQLAlchemyError:
        db.rollback()


def process_meeting_transcription_task(meeting_id: int) -> None:
    """Background task that extracts audio, transcribes locally, and persists results."""
    db = SessionLocal()
    try:
        meeting = db.scalar(select(Meeting).where(Meeting.id == meeting_id))
        if meeting is None:
            return

        with extract_normalized_audio(meeting.storage_path) as wav_path:
            result = transcribe_audio(wav_path)

        transcript = db.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting_id)
        )
        if transcript is None:
            transcript = MeetingTranscript(
                meeting_id=meeting_id,
                full_text=result.full_text,
                language=result.language,
                language_probability=result.language_probability,
                duration_seconds=result.duration_seconds,
                model_name=result.model_name,
                segments=result.segments,
            )
            db.add(transcript)
        else:
            transcript.full_text = result.full_text
            transcript.language = result.language
            transcript.language_probability = result.language_probability
            transcript.duration_seconds = result.duration_seconds
            transcript.model_name = result.model_name
            transcript.segments = result.segments

        meeting.duration_seconds = result.duration_seconds
        meeting.processing_status = "transcribed"
        meeting.processing_error = None
        db.commit()
    except (MediaProcessingError, TranscriptionError) as exc:
        db.rollback()
        _mark_transcription_failed(db, meeting_id, str(exc))
    except SQLAlchemyError:
        db.rollback()
        _mark_transcription_failed(
            db,
            meeting_id,
            "Failed to save transcription results to the database.",
        )
    except Exception:
        db.rollback()
        _mark_transcription_failed(
            db,
            meeting_id,
            "An unexpected error occurred during media transcription.",
        )
    finally:
        db.close()


def get_user_meeting_transcript(
    db: Session,
    meeting_id: int,
    user_id: int,
) -> MeetingTranscript:
    """Retrieve the transcript for an authenticated user's meeting or raise 404."""
    meeting = get_user_meeting(db, meeting_id, user_id)
    transcript = db.scalar(
        select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.id)
    )
    if transcript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found for this meeting.",
        )
    return transcript
