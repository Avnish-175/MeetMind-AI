import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  Clock,
  FileAudio,
  FileText,
  FileVideo,
  HardDrive,
  Info,
  Trash2,
} from 'lucide-react';
import { DeleteMeetingModal } from '../../components/meetings/DeleteMeetingModal';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { useMeetingStore } from '../../store/useMeetingStore';
import {
  formatDuration,
  formatFileSize,
  formatMeetingDate,
  getStatusBadgeInfo,
} from '../../utils/meetingFormat';

export function MeetingDetailPage() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const navigate = useNavigate();

  const {
    selectedMeeting,
    isLoadingDetail,
    isDeletingId,
    detailError,
    loadMeetingById,
    removeMeeting,
    clearSelectedMeeting,
  } = useMeetingStore();

  useDocumentTitle(selectedMeeting ? selectedMeeting.title : 'Meeting Details');

  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const numericId = meetingId ? Number(meetingId) : NaN;
  const isValidId = Number.isInteger(numericId) && numericId > 0;

  useEffect(() => {
    if (!isValidId) {
      return;
    }
    void loadMeetingById(numericId);
    return () => {
      clearSelectedMeeting();
    };
  }, [isValidId, numericId, loadMeetingById, clearSelectedMeeting]);

  const handleConfirmDelete = async () => {
    if (!selectedMeeting) {
      return;
    }
    setDeleteError(null);
    try {
      await removeMeeting(selectedMeeting.id);
      setIsDeleteOpen(false);
      navigate('/meetings', { replace: true });
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : 'Failed to delete meeting.'
      );
    }
  };

  if (!isValidId) {
    return (
      <div className="space-y-4">
        <Link
          to="/meetings"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Meetings
        </Link>
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          Invalid meeting identifier.
        </div>
      </div>
    );
  }

  if (isLoadingDetail) {
    return (
      <div className="space-y-6">
        <div className="h-5 w-32 animate-pulse rounded bg-slate-200" />
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="h-7 w-1/2 animate-pulse rounded bg-slate-200" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
          <div className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((idx) => (
              <div key={idx} className="h-16 animate-pulse rounded-lg bg-slate-100" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (detailError || !selectedMeeting) {
    return (
      <div className="space-y-4">
        <Link
          to="/meetings"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Meetings
        </Link>
        <div
          role="alert"
          className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-semibold">Unable to load meeting</p>
              <p className="mt-0.5">
                {detailError ?? 'This meeting could not be found or you do not have access to it.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => navigate('/meetings')}
            className="w-fit rounded-lg border border-rose-200 bg-white px-4 py-2 text-xs font-medium text-rose-700 hover:bg-rose-100"
          >
            Return to Meetings
          </button>
        </div>
      </div>
    );
  }

  const statusBadge = getStatusBadgeInfo(selectedMeeting.processing_status);
  const isVideo = selectedMeeting.media_type === 'video';

  return (
    <div className="space-y-6">
      {/* Breadcrumb Back Navigation */}
      <div>
        <Link
          to="/meetings"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 transition-colors hover:text-slate-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Meetings
        </Link>
      </div>

      {/* Header Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${
                isVideo
                  ? 'bg-violet-50 text-violet-600'
                  : 'bg-indigo-50 text-indigo-600'
              }`}
            >
              {isVideo ? (
                <FileVideo className="h-6 w-6" />
              ) : (
                <FileAudio className="h-6 w-6" />
              )}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">
                  {selectedMeeting.title}
                </h1>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge.className}`}
                >
                  {statusBadge.label}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-slate-600">
                {selectedMeeting.description || 'No description provided for this meeting.'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => {
              setDeleteError(null);
              setIsDeleteOpen(true);
            }}
            className="inline-flex w-fit items-center gap-2 rounded-lg border border-rose-200 bg-white px-3.5 py-2 text-sm font-medium text-rose-600 shadow-2xs transition-colors hover:bg-rose-50"
          >
            <Trash2 className="h-4 w-4" />
            Delete Meeting
          </button>
        </div>
      </div>

      {/* Metadata Grid */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <h2 className="text-base font-semibold text-slate-900">Meeting Metadata</h2>
        <p className="mt-0.5 text-xs text-slate-500">
          File and storage details for this uploaded recording.
        </p>

        <dl className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
              {isVideo ? (
                <FileVideo className="h-3.5 w-3.5 text-violet-500" />
              ) : (
                <FileAudio className="h-3.5 w-3.5 text-indigo-500" />
              )}
              Media Type
            </dt>
            <dd className="mt-1.5 text-sm font-semibold capitalize text-slate-900">
              {selectedMeeting.media_type}
            </dd>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <FileText className="h-3.5 w-3.5 text-slate-400" />
              Original Filename
            </dt>
            <dd
              className="mt-1.5 truncate text-sm font-semibold text-slate-900"
              title={selectedMeeting.original_filename}
            >
              {selectedMeeting.original_filename}
            </dd>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <HardDrive className="h-3.5 w-3.5 text-slate-400" />
              File Size
            </dt>
            <dd className="mt-1.5 text-sm font-semibold text-slate-900">
              {formatFileSize(selectedMeeting.file_size_bytes)}
              <span className="ml-1.5 text-xs font-normal text-slate-500">
                ({selectedMeeting.file_size_bytes.toLocaleString()} bytes)
              </span>
            </dd>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              Upload Date
            </dt>
            <dd className="mt-1.5 text-sm font-semibold text-slate-900">
              {formatMeetingDate(selectedMeeting.created_at)}
            </dd>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              Duration
            </dt>
            <dd className="mt-1.5 text-sm font-semibold text-slate-900">
              {formatDuration(selectedMeeting.duration_seconds)}
            </dd>
          </div>

          <div className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <Info className="h-3.5 w-3.5 text-slate-400" />
              MIME Type &amp; ID
            </dt>
            <dd className="mt-1.5 text-sm font-semibold text-slate-900">
              {selectedMeeting.mime_type}
              <span className="ml-1.5 text-xs font-normal text-slate-500">
                • #{selectedMeeting.id}
              </span>
            </dd>
          </div>
        </dl>
      </section>

      {/* Processing Notice */}
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
        <p>
          This meeting media file is stored locally and ready for future transcription and AI
          analysis workflows.
        </p>
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteMeetingModal
        isOpen={isDeleteOpen}
        meetingTitle={selectedMeeting.title}
        isDeleting={isDeletingId === selectedMeeting.id}
        error={deleteError}
        onCancel={() => {
          setDeleteError(null);
          setIsDeleteOpen(false);
        }}
        onConfirm={() => void handleConfirmDelete()}
      />
    </div>
  );
}
