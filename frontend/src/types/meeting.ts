export type MeetingMediaType = 'audio' | 'video';

export type MeetingProcessingStatus =
  | 'uploaded'
  | 'processing'
  | 'completed'
  | 'failed'
  | (string & {});

export interface Meeting {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  media_type: MeetingMediaType;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  duration_seconds: number | null;
  processing_status: MeetingProcessingStatus;
  created_at: string;
  updated_at: string;
}

export interface MeetingListResponse {
  items: Meeting[];
  total: number;
}

export interface UploadMeetingPayload {
  title: string;
  description?: string;
  file: File;
  onUploadProgress?: (progressPercent: number) => void;
  signal?: AbortSignal;
}
