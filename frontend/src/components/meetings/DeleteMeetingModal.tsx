import { useEffect } from 'react';
import { AlertTriangle, Loader2, X } from 'lucide-react';

interface DeleteMeetingModalProps {
  isOpen: boolean;
  meetingTitle: string;
  isDeleting: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteMeetingModal({
  isOpen,
  meetingTitle,
  isDeleting,
  error,
  onCancel,
  onConfirm,
}: DeleteMeetingModalProps) {
  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isDeleting) {
        onCancel();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isDeleting, onCancel]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-meeting-modal-title"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-rose-50 text-rose-600">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="delete-meeting-modal-title"
                className="text-base font-semibold text-slate-900"
              >
                Delete Meeting
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                Are you sure you want to delete{' '}
                <span className="font-medium text-slate-900">"{meetingTitle}"</span>? This
                will permanently remove the meeting record and its uploaded media file.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            aria-label="Close dialog"
            className="rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700"
          >
            {error}
          </div>
        )}

        <div className="mt-6 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white shadow-xs transition-colors hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDeleting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Meeting'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
