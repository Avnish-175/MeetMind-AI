from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreateMetadata
from app.services.storage_service import delete_stored_file, save_upload_file


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
