from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.database.dependencies import get_db
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.meeting import MeetingListResponse, MeetingResponse
from app.services.meeting_service import (
    create_meeting,
    delete_user_meeting,
    get_user_meeting,
    list_user_meetings,
)

router = APIRouter(prefix="/api/v1/meetings", tags=["Meetings"])


@router.post(
    "",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_meeting(
    title: str = Form(...),
    description: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    """Upload a meeting audio/video file and create a meeting record."""
    return await create_meeting(
        db=db,
        user_id=current_user.id,
        title=title,
        description=description,
        upload_file=file,
    )


@router.get(
    "",
    response_model=MeetingListResponse,
    status_code=status.HTTP_200_OK,
)
def list_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingListResponse:
    """List all meetings belonging to the authenticated user."""
    items = list_user_meetings(db=db, user_id=current_user.id)
    return MeetingListResponse(items=items, total=len(items))


@router.get(
    "/{meeting_id}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
)
def get_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    """Retrieve a single meeting belonging to the authenticated user."""
    return get_user_meeting(db=db, meeting_id=meeting_id, user_id=current_user.id)


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a meeting and its associated media file."""
    delete_user_meeting(db=db, meeting_id=meeting_id, user_id=current_user.id)
