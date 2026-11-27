import { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  FileAudio,
  FileVideo,
  Loader2,
  UploadCloud,
  X,
} from 'lucide-react';
import {
  extractMeetingErrorMessage,
  isRequestCanceled,
  uploadMeeting,
} from '../../services/meetingApi';
import type { Meeting } from '../../types/meeting';
import {
  ALLOWED_AUDIO_EXTENSIONS,
  ALLOWED_MEDIA_ACCEPT,
  ALLOWED_VIDEO_EXTENSIONS,
  MAX_UPLOAD_SIZE_BYTES,
  MAX_UPLOAD_SIZE_MB,
  formatFileSize,
  inferMediaKindFromFilename,
  isSupportedMediaFile,
} from '../../utils/meetingFormat';

interface UploadMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (meeting: Meeting) => void | Promise<void>;
}

export function UploadMeetingModal({
  isOpen,
  onClose,
  onSuccess,
}: UploadMeetingModalProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isUploading) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isUploading, onClose]);

  if (!isOpen) {
    return null;
  }

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setSelectedFile(null);
    setIsDragging(false);
    setIsUploading(false);
    setUploadProgress(0);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (isUploading && abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      return;
    }
    resetForm();
    onClose();
  };

  const validateAndSelectFile = (file: File | undefined | null) => {
    if (!file) {
      return;
    }

    if (!isSupportedMediaFile(file)) {
      setError(
        `Unsupported file format. Supported audio: ${ALLOWED_AUDIO_EXTENSIONS.join(', ')}. Supported video: ${ALLOWED_VIDEO_EXTENSIONS.join(', ')}.`
      );
      return;
    }

    if (file.size === 0) {
      setError('The selected file is empty. Please choose a valid media file.');
      return;
    }

    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      setError(`File exceeds the maximum allowed size of ${MAX_UPLOAD_SIZE_MB} MB.`);
      return;
    }

    setError(null);
    setSelectedFile(file);

    if (!title.trim()) {
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
      if (nameWithoutExt) {
        setTitle(nameWithoutExt.slice(0, 255));
      }
    }
  };

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    validateAndSelectFile(event.target.files?.[0]);
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!isUploading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
    if (isUploading) {
      return;
    }
    validateAndSelectFile(event.dataTransfer.files?.[0]);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError('Please enter a meeting title.');
      return;
    }
    if (trimmedTitle.length > 255) {
      setError('Meeting title must be 255 characters or fewer.');
      return;
    }
    if (description.trim().length > 2000) {
      setError('Description must be 2000 characters or fewer.');
      return;
    }
    if (!selectedFile) {
      setError('Please select an audio or video file to upload.');
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const created = await uploadMeeting({
        title: trimmedTitle,
        description,
        file: selectedFile,
        onUploadProgress: (percent) => setUploadProgress(percent),
        signal: controller.signal,
      });

      abortControllerRef.current = null;
      resetForm();
      await onSuccess(created);
      onClose();
    } catch (err) {
      abortControllerRef.current = null;
      setIsUploading(false);
      setUploadProgress(0);

      if (isRequestCanceled(err)) {
        setError('Upload canceled. You can modify your selection or try again.');
        return;
      }
      setError(extractMeetingErrorMessage(err, 'Failed to upload meeting.'));
    }
  };

  const mediaKind = selectedFile ? inferMediaKindFromFilename(selectedFile.name) : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-meeting-modal-title"
    >
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2
              id="upload-meeting-modal-title"
              className="text-lg font-semibold text-slate-900"
            >
              Upload Meeting
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Add an audio or video recording to your local workspace.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={isUploading}
            aria-label="Close modal"
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 px-6 py-5">
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Drag & Drop / File Browser */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Media file <span className="text-rose-500">*</span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept={ALLOWED_MEDIA_ACCEPT}
              onChange={handleFileInputChange}
              disabled={isUploading}
              className="sr-only"
              id="meeting-file-input"
            />

            {!selectedFile ? (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !isUploading && fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && !isUploading) {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                className={`mt-1.5 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-7 text-center transition-colors ${
                  isDragging
                    ? 'border-indigo-500 bg-indigo-50/60'
                    : 'border-slate-300 bg-slate-50/70 hover:border-indigo-400 hover:bg-slate-50'
                }`}
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                  <UploadCloud className="h-5 w-5" />
                </div>
                <p className="mt-3 text-sm font-medium text-slate-700">
                  Drag and drop your file here, or{' '}
                  <span className="text-indigo-600 underline decoration-indigo-300 underline-offset-2">
                    browse
                  </span>
                </p>
                <p className="mt-1.5 text-xs text-slate-500">
                  Audio: MP3, WAV, M4A, OGG, FLAC, AAC • Video: MP4, WEBM, MOV, MKV, AVI
                </p>
                <p className="mt-0.5 text-[11px] text-slate-400">
                  Maximum file size: {MAX_UPLOAD_SIZE_MB} MB
                </p>
              </div>
            ) : (
              <div className="mt-1.5 flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                      mediaKind === 'video'
                        ? 'bg-violet-100 text-violet-600'
                        : 'bg-indigo-100 text-indigo-600'
                    }`}
                  >
                    {mediaKind === 'video' ? (
                      <FileVideo className="h-5 w-5" />
                    ) : (
                      <FileAudio className="h-5 w-5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {selectedFile.name}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {formatFileSize(selectedFile.size)}
                      {mediaKind ? ` • ${mediaKind.toUpperCase()}` : ''}
                    </p>
                  </div>
                </div>
                {!isUploading && (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedFile(null);
                      if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                      }
                    }}
                    className="shrink-0 rounded-md px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200/70 hover:text-slate-900"
                  >
                    Change
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Meeting Title */}
          <div>
            <label
              htmlFor="meeting-title-input"
              className="block text-sm font-medium text-slate-700"
            >
              Meeting title <span className="text-rose-500">*</span>
            </label>
            <input
              id="meeting-title-input"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isUploading}
              maxLength={255}
              placeholder="e.g., Q4 Architecture Sync"
              required
              className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 shadow-2xs transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none disabled:bg-slate-100"
            />
          </div>

          {/* Optional Description */}
          <div>
            <label
              htmlFor="meeting-description-input"
              className="block text-sm font-medium text-slate-700"
            >
              Description <span className="text-xs font-normal text-slate-400">(optional)</span>
            </label>
            <textarea
              id="meeting-description-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isUploading}
              maxLength={2000}
              rows={3}
              placeholder="Add agenda, participants, or context for this meeting..."
              className="mt-1.5 block w-full resize-none rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 shadow-2xs transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none disabled:bg-slate-100"
            />
          </div>

          {/* Upload Progress */}
          {isUploading && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-medium text-slate-600">
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                  {uploadProgress < 100 ? 'Uploading media...' : 'Finalizing meeting...'}
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-indigo-600 transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Footer Controls */}
          <div className="flex items-center justify-end gap-2.5 border-t border-slate-100 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              {isUploading ? 'Cancel Upload' : 'Cancel'}
            </button>
            <button
              type="submit"
              disabled={isUploading}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-xs transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                'Upload Meeting'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
