import axios from 'axios';
import api from './api';
import type {
  IndexingStartResponse,
  Meeting,
  MeetingAnalysis,
  MeetingListResponse,
  MeetingTranscript,
  StartAnalysisResponse,
  UploadMeetingPayload,
} from '../types/meeting';

export async function fetchMeetings(): Promise<MeetingListResponse> {
  const response = await api.get<MeetingListResponse>('/api/v1/meetings');
  return response.data;
}

export async function fetchMeetingById(meetingId: number): Promise<Meeting> {
  const response = await api.get<Meeting>(`/api/v1/meetings/${meetingId}`);
  return response.data;
}

export async function uploadMeeting({
  title,
  description,
  file,
  onUploadProgress,
  signal,
}: UploadMeetingPayload): Promise<Meeting> {
  const formData = new FormData();
  formData.append('title', title.trim());

  const trimmedDescription = description?.trim();
  if (trimmedDescription) {
    formData.append('description', trimmedDescription);
  }

  formData.append('file', file);

  const response = await api.post<Meeting>('/api/v1/meetings', formData, {
    timeout: 0,
    signal,
    onUploadProgress: (event) => {
      if (!onUploadProgress || !event.total) {
        return;
      }
      const percent = Math.min(100, Math.round((event.loaded * 100) / event.total));
      onUploadProgress(percent);
    },
  });

  return response.data;
}

export async function deleteMeeting(meetingId: number): Promise<void> {
  await api.delete(`/api/v1/meetings/${meetingId}`);
}

export async function fetchMeetingTranscript(
  meetingId: number
): Promise<MeetingTranscript | null> {
  try {
    const response = await api.get<MeetingTranscript>(
      `/api/v1/meetings/${meetingId}/transcript`
    );
    return response.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function startMeetingTranscription(
  meetingId: number
): Promise<{ meeting_id: number; processing_status: string; message: string }> {
  const response = await api.post<{
    meeting_id: number;
    processing_status: string;
    message: string;
  }>(`/api/v1/meetings/${meetingId}/transcribe`);
  return response.data;
}

export async function fetchMeetingAnalysis(
  meetingId: number
): Promise<MeetingAnalysis | null> {
  try {
    const response = await api.get<MeetingAnalysis>(
      `/api/v1/meetings/${meetingId}/analysis`
    );
    return response.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function startMeetingAnalysis(
  meetingId: number
): Promise<StartAnalysisResponse> {
  const response = await api.post<StartAnalysisResponse>(
    `/api/v1/meetings/${meetingId}/analyze`
  );
  return response.data;
}

export async function startMeetingIndexing(
  meetingId: number
): Promise<IndexingStartResponse> {
  const response = await api.post<IndexingStartResponse>(
    `/api/v1/meetings/${meetingId}/index`
  );
  return response.data;
}

export function isRequestCanceled(error: unknown): boolean {
  return axios.isCancel(error);
}

export function extractMeetingErrorMessage(
  error: unknown,
  fallback = 'An unexpected error occurred. Please try again.'
): string {
  if (axios.isCancel(error)) {
    return 'Upload was canceled.';
  }

  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return 'Unable to connect to the server. Please check your connection and try again.';
    }

    const detail = error.response.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    const status = error.response.status;
    if (status === 401) {
      return 'Your session has expired. Please sign in again.';
    }
    if (status === 404) {
      return 'Meeting not found.';
    }
    if (status === 413) {
      return 'The selected file exceeds the maximum allowed upload size.';
    }
    if (status === 415) {
      return 'Unsupported media format. Please choose a valid audio or video file.';
    }
    if (status === 422) {
      return 'Please check the meeting title, description, and selected file.';
    }
    if (status >= 500) {
      return 'A server error occurred while processing your request. Please try again.';
    }
  }

  return fallback;
}
