import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Eye,
  FileAudio,
  FileVideo,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Video,
} from 'lucide-react';
import { DeleteMeetingModal } from '../../components/meetings/DeleteMeetingModal';
import { UploadMeetingModal } from '../../components/meetings/UploadMeetingModal';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { useMeetingStore } from '../../store/useMeetingStore';
import type { Meeting } from '../../types/meeting';
import {
  formatFileSize,
  formatMeetingDate,
  getStatusBadgeInfo,
} from '../../utils/meetingFormat';

type MediaFilter = 'all' | 'audio' | 'video';

export function MeetingsPage() {
  useDocumentTitle('Meetings');
  const navigate = useNavigate();

  const {
    meetings,
    isLoading,
    isDeletingId,
    error,
    loadMeetings,
    removeMeeting,
  } = useMeetingStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [mediaFilter, setMediaFilter] = useState<MediaFilter>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [meetingToDelete, setMeetingToDelete] = useState<Meeting | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    void loadMeetings();
  }, [loadMeetings]);

  const statusOptions = useMemo(() => {
    const base = new Set(['uploaded', 'processing', 'completed', 'failed']);
    for (const meeting of meetings) {
      if (meeting.processing_status) {
        base.add(meeting.processing_status.toLowerCase());
      }
    }
    return Array.from(base);
  }, [meetings]);

  const filteredMeetings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return meetings.filter((meeting) => {
      if (mediaFilter !== 'all' && meeting.media_type !== mediaFilter) {
        return false;
      }
      if (
        statusFilter !== 'all' &&
        meeting.processing_status.toLowerCase() !== statusFilter
      ) {
        return false;
      }
      if (!query) {
        return true;
      }
      return (
        meeting.title.toLowerCase().includes(query) ||
        (meeting.description ?? '').toLowerCase().includes(query) ||
        meeting.original_filename.toLowerCase().includes(query)
      );
    });
  }, [meetings, searchQuery, mediaFilter, statusFilter]);

  const hasActiveFilters =
    searchQuery.trim() !== '' || mediaFilter !== 'all' || statusFilter !== 'all';

  const handleResetFilters = () => {
    setSearchQuery('');
    setMediaFilter('all');
    setStatusFilter('all');
  };

  const handleConfirmDelete = async () => {
    if (!meetingToDelete) {
      return;
    }
    setDeleteError(null);
    try {
      await removeMeeting(meetingToDelete.id);
      setMeetingToDelete(null);
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : 'Failed to delete meeting.'
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Heading & Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Meetings
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Upload, organize, and manage your local audio and video meeting recordings.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => void loadMeetings()}
            disabled={isLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-xs transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw
              className={`h-4 w-4 text-slate-500 ${isLoading ? 'animate-spin' : ''}`}
            />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setIsUploadOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-xs transition-colors hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Upload Meeting
          </button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by meeting title, description, or filename..."
              aria-label="Search meetings"
              className="block w-full rounded-lg border border-slate-200 bg-slate-50/60 py-2 pr-3 pl-9 text-sm text-slate-900 placeholder-slate-400 transition-colors focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Media Type Filter */}
            <div
              className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5"
              role="group"
              aria-label="Filter by media type"
            >
              {(['all', 'audio', 'video'] as const).map((type) => {
                const active = mediaFilter === type;
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setMediaFilter(type)}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                      active
                        ? 'bg-white text-slate-900 shadow-2xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {type === 'all' ? 'All Media' : type}
                  </button>
                );
              })}
            </div>

            {/* Processing Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by processing status"
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
            >
              <option value="all">All Statuses</option>
              {statusOptions.map((statusValue) => (
                <option key={statusValue} value={statusValue}>
                  {getStatusBadgeInfo(statusValue).label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div
          role="alert"
          className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => void loadMeetings()}
            className="w-fit rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs font-medium text-rose-700 transition-colors hover:bg-rose-100"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && meetings.length === 0 ? (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="flex animate-pulse items-center justify-between gap-4 border-b border-slate-100 pb-4 last:border-0 last:pb-0"
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-slate-200" />
                <div className="space-y-2">
                  <div className="h-4 w-48 rounded bg-slate-200" />
                  <div className="h-3 w-32 rounded bg-slate-100" />
                </div>
              </div>
              <div className="h-6 w-20 rounded-full bg-slate-100" />
            </div>
          ))}
        </div>
      ) : filteredMeetings.length === 0 ? (
        /* Empty State */
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center shadow-xs">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
            <Video className="h-6 w-6" />
          </div>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            {hasActiveFilters ? 'No matching meetings found' : 'No meetings uploaded yet'}
          </h2>
          <p className="mt-1.5 max-w-sm text-sm text-slate-500">
            {hasActiveFilters
              ? 'Try adjusting your search query or clearing the active media and status filters.'
              : 'Upload an audio or video recording to start organizing your meetings locally.'}
          </p>
          <div className="mt-5">
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={handleResetFilters}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-2xs transition-colors hover:bg-slate-50"
              >
                Clear Filters
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsUploadOpen(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-xs transition-colors hover:bg-indigo-700"
              >
                <Plus className="h-4 w-4" />
                Upload Meeting
              </button>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs md:block">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left">
                <thead className="bg-slate-50/80">
                  <tr>
                    <th className="px-5 py-3.5 text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Meeting
                    </th>
                    <th className="px-4 py-3.5 text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Media Type
                    </th>
                    <th className="px-4 py-3.5 text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      File Size
                    </th>
                    <th className="px-4 py-3.5 text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Uploaded
                    </th>
                    <th className="px-4 py-3.5 text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Status
                    </th>
                    <th className="px-5 py-3.5 text-right text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredMeetings.map((meeting) => {
                    const statusBadge = getStatusBadgeInfo(meeting.processing_status);
                    const isVideo = meeting.media_type === 'video';
                    return (
                      <tr
                        key={meeting.id}
                        className="transition-colors hover:bg-slate-50/70"
                      >
                        <td className="px-5 py-4">
                          <Link
                            to={`/meetings/${meeting.id}`}
                            className="group flex items-start gap-3"
                          >
                            <div
                              className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                                isVideo
                                  ? 'bg-violet-50 text-violet-600'
                                  : 'bg-indigo-50 text-indigo-600'
                              }`}
                            >
                              {isVideo ? (
                                <FileVideo className="h-4 w-4" />
                              ) : (
                                <FileAudio className="h-4 w-4" />
                              )}
                            </div>
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-slate-900 group-hover:text-indigo-600">
                                {meeting.title}
                              </p>
                              <p className="mt-0.5 truncate text-xs text-slate-500">
                                {meeting.original_filename}
                              </p>
                            </div>
                          </Link>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium capitalize text-slate-700">
                            {meeting.media_type}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-sm whitespace-nowrap text-slate-600">
                          {formatFileSize(meeting.file_size_bytes)}
                        </td>
                        <td className="px-4 py-4 text-sm whitespace-nowrap text-slate-600">
                          {formatMeetingDate(meeting.created_at)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge.className}`}
                          >
                            {statusBadge.label}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => navigate(`/meetings/${meeting.id}`)}
                              title="View meeting details"
                              aria-label={`View ${meeting.title}`}
                              className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-indigo-600"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setDeleteError(null);
                                setMeetingToDelete(meeting);
                              }}
                              disabled={isDeletingId === meeting.id}
                              title="Delete meeting"
                              aria-label={`Delete ${meeting.title}`}
                              className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile Cards */}
          <div className="space-y-3 md:hidden">
            {filteredMeetings.map((meeting) => {
              const statusBadge = getStatusBadgeInfo(meeting.processing_status);
              const isVideo = meeting.media_type === 'video';
              return (
                <div
                  key={meeting.id}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <Link
                      to={`/meetings/${meeting.id}`}
                      className="flex min-w-0 items-start gap-3"
                    >
                      <div
                        className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                          isVideo
                            ? 'bg-violet-50 text-violet-600'
                            : 'bg-indigo-50 text-indigo-600'
                        }`}
                      >
                        {isVideo ? (
                          <FileVideo className="h-4 w-4" />
                        ) : (
                          <FileAudio className="h-4 w-4" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-900">
                          {meeting.title}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-slate-500">
                          {meeting.original_filename}
                        </p>
                      </div>
                    </Link>

                    <span
                      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge.className}`}
                    >
                      {statusBadge.label}
                    </span>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-slate-100 px-2 py-0.5 font-medium capitalize text-slate-700">
                        {meeting.media_type}
                      </span>
                      <span>•</span>
                      <span>{formatFileSize(meeting.file_size_bytes)}</span>
                      <span>•</span>
                      <span>{formatMeetingDate(meeting.created_at)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/meetings/${meeting.id}`}
                        className="font-medium text-indigo-600 hover:text-indigo-700"
                      >
                        Details
                      </Link>
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteError(null);
                          setMeetingToDelete(meeting);
                        }}
                        className="font-medium text-rose-600 hover:text-rose-700"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Upload Modal */}
      <UploadMeetingModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={async () => {
          await loadMeetings();
        }}
      />

      {/* Delete Confirmation Modal */}
      <DeleteMeetingModal
        isOpen={meetingToDelete !== null}
        meetingTitle={meetingToDelete?.title ?? ''}
        isDeleting={isDeletingId !== null}
        error={deleteError}
        onCancel={() => {
          setDeleteError(null);
          setMeetingToDelete(null);
        }}
        onConfirm={() => void handleConfirmDelete()}
      />
    </div>
  );
}
