export const MAX_UPLOAD_SIZE_MB = 200;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

export const ALLOWED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'] as const;
export const ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov', '.mkv', '.avi'] as const;
export const ALLOWED_MEDIA_EXTENSIONS = [
  ...ALLOWED_AUDIO_EXTENSIONS,
  ...ALLOWED_VIDEO_EXTENSIONS,
] as const;

export const ALLOWED_MEDIA_ACCEPT = [
  ...ALLOWED_MEDIA_EXTENSIONS,
  'audio/*',
  'video/*',
].join(',');

export function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf('.');
  if (lastDot <= 0) {
    return '';
  }
  return filename.slice(lastDot).toLowerCase();
}

export function isSupportedMediaFile(file: File): boolean {
  const ext = getFileExtension(file.name);
  return (ALLOWED_MEDIA_EXTENSIONS as readonly string[]).includes(ext);
}

export function inferMediaKindFromFilename(filename: string): 'audio' | 'video' | null {
  const ext = getFileExtension(filename);
  if ((ALLOWED_AUDIO_EXTENSIONS as readonly string[]).includes(ext)) {
    return 'audio';
  }
  if ((ALLOWED_VIDEO_EXTENSIONS as readonly string[]).includes(ext)) {
    return 'video';
  }
  return null;
}

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return '0 B';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 100 ? 0 : value >= 10 ? 1 : 2)} ${units[unitIndex]}`;
}

export function formatMeetingDate(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return 'Unknown date';
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) {
    return 'Not yet available';
  }
  const totalSeconds = Math.round(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
}

export function getStatusBadgeInfo(status: string): {
  label: string;
  className: string;
} {
  const normalized = status.toLowerCase();
  switch (normalized) {
    case 'uploaded':
      return {
        label: 'Uploaded',
        className: 'bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200',
      };
    case 'processing':
      return {
        label: 'Processing',
        className: 'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200',
      };
    case 'completed':
    case 'processed':
      return {
        label: 'Completed',
        className: 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200',
      };
    case 'failed':
      return {
        label: 'Failed',
        className: 'bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200',
      };
    default:
      return {
        label: status.charAt(0).toUpperCase() + status.slice(1),
        className: 'bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-200',
      };
  }
}
