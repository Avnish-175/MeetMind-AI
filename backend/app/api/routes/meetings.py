import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.database.dependencies import get_db
from app.models.meeting import Meeting
from app.models.transcript import MeetingTranscript
from app.models.user import User
from app.schemas.meeting import (
    MeetingListResponse,
    MeetingResponse,
    TranscriptionStartResponse,
)
from app.schemas.meeting_analysis import MeetingAnalysisResponse
from app.schemas.transcript import MeetingTranscriptResponse
from app.services.analysis_orchestrator import (
    process_meeting_analysis_task,
    start_meeting_analysis_job,
)
from app.services.meeting_analysis_service import get_meeting_analysis
from app.services.meeting_service import (
    create_meeting,
    delete_user_meeting,
    get_user_meeting,
    get_user_meeting_transcript,
    list_user_meetings,
    process_meeting_transcription_task,
    start_meeting_transcription,
)

router = APIRouter(prefix="/api/v1/meetings", tags=["Meetings"])
logger = logging.getLogger(__name__)


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


@router.post(
    "/{meeting_id}/transcribe",
    response_model=TranscriptionStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def transcribe_meeting(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TranscriptionStartResponse:
    """Start background audio extraction and local Whisper transcription for a meeting."""
    meeting = start_meeting_transcription(
        db=db,
        meeting_id=meeting_id,
        user_id=current_user.id,
    )
    background_tasks.add_task(process_meeting_transcription_task, meeting.id)
    logger.info(
        "Enqueued background transcription task for meeting ID=%d (requested by user ID=%d)",
        meeting.id,
        current_user.id,
    )
    return TranscriptionStartResponse(
        meeting_id=meeting.id,
        processing_status=meeting.processing_status,
        message="Meeting transcription started.",
    )


@router.get(
    "/{meeting_id}/transcript",
    response_model=MeetingTranscriptResponse,
    status_code=status.HTTP_200_OK,
)
def get_meeting_transcript(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeetingTranscript:
    """Retrieve the transcript and timestamped segments for a meeting."""
    return get_user_meeting_transcript(
        db=db,
        meeting_id=meeting_id,
        user_id=current_user.id,
    )


@router.post(
    "/{meeting_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_meeting(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Start background meeting intelligence and contextual analysis using local NLP and Ollama."""
    analysis = start_meeting_analysis_job(
        db=db,
        meeting_id=meeting_id,
        user_id=current_user.id,
    )
    background_tasks.add_task(process_meeting_analysis_task, meeting_id)
    logger.info(
        "Enqueued background analysis task for meeting ID=%d (requested by user ID=%d)",
        meeting_id,
        current_user.id,
    )
    return {
        "meeting_id": meeting_id,
        "status": analysis.status,
        "message": "Meeting analysis job started successfully.",
    }


@router.get(
    "/{meeting_id}/analysis",
    response_model=MeetingAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
def get_meeting_analysis_endpoint(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve structured meeting analysis, summaries, action items, and insights."""
    return get_meeting_analysis(
        db=db,
        meeting_id=meeting_id,
        user_id=current_user.id,
    )
