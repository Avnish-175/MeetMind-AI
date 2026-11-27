import { create } from 'zustand';
import {
  deleteMeeting,
  extractMeetingErrorMessage,
  fetchMeetingAnalysis,
  fetchMeetingById,
  fetchMeetingTranscript,
  fetchMeetings,
  startMeetingAnalysis,
  startMeetingTranscription,
} from '../services/meetingApi';
import type {
  Meeting,
  MeetingAnalysis,
  MeetingTranscript,
} from '../types/meeting';

interface MeetingState {
  meetings: Meeting[];
  total: number;
  selectedMeeting: Meeting | null;
  transcript: MeetingTranscript | null;
  analysis: MeetingAnalysis | null;
  isLoading: boolean;
  isLoadingDetail: boolean;
  isLoadingTranscript: boolean;
  isLoadingAnalysis: boolean;
  isStartingTranscription: boolean;
  isStartingAnalysis: boolean;
  isDeletingId: number | null;
  error: string | null;
  detailError: string | null;
  transcriptError: string | null;
  analysisError: string | null;
  loadMeetings: () => Promise<void>;
  loadMeetingById: (meetingId: number, silent?: boolean) => Promise<void>;
  loadTranscript: (meetingId: number, silent?: boolean) => Promise<void>;
  loadAnalysis: (meetingId: number, silent?: boolean) => Promise<MeetingAnalysis | null>;
  triggerTranscription: (meetingId: number) => Promise<void>;
  triggerAnalysis: (meetingId: number) => Promise<void>;
  removeMeeting: (meetingId: number) => Promise<void>;
  clearSelectedMeeting: () => void;
  clearMeetings: () => void;
  clearError: () => void;
}

export const useMeetingStore = create<MeetingState>((set, get) => ({
  meetings: [],
  total: 0,
  selectedMeeting: null,
  transcript: null,
  analysis: null,
  isLoading: false,
  isLoadingDetail: false,
  isLoadingTranscript: false,
  isLoadingAnalysis: false,
  isStartingTranscription: false,
  isStartingAnalysis: false,
  isDeletingId: null,
  error: null,
  detailError: null,
  transcriptError: null,
  analysisError: null,

  loadMeetings: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await fetchMeetings();
      set({
        meetings: data.items,
        total: data.total,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      set({
        isLoading: false,
        error: extractMeetingErrorMessage(err, 'Failed to load meetings.'),
      });
    }
  },

  loadMeetingById: async (meetingId: number, silent = false) => {
    if (!silent) {
      set({ isLoadingDetail: true, detailError: null, selectedMeeting: null });
    }
    try {
      const meeting = await fetchMeetingById(meetingId);
      set({
        selectedMeeting: meeting,
        isLoadingDetail: false,
        detailError: null,
      });
    } catch (err) {
      set({
        selectedMeeting: silent ? get().selectedMeeting : null,
        isLoadingDetail: false,
        detailError: extractMeetingErrorMessage(err, 'Failed to load meeting details.'),
      });
    }
  },

  loadTranscript: async (meetingId: number, silent = false) => {
    if (!silent) {
      set({ isLoadingTranscript: true, transcriptError: null });
    }
    try {
      const transcript = await fetchMeetingTranscript(meetingId);
      set({
        transcript,
        isLoadingTranscript: false,
        transcriptError: null,
      });
    } catch (err) {
      set({
        isLoadingTranscript: false,
        transcriptError: extractMeetingErrorMessage(err, 'Failed to load meeting transcript.'),
      });
    }
  },

  loadAnalysis: async (meetingId: number, silent = false) => {
    if (!silent) {
      set({ isLoadingAnalysis: true, analysisError: null });
    }
    try {
      const analysis = await fetchMeetingAnalysis(meetingId);
      set({
        analysis,
        isLoadingAnalysis: false,
        analysisError: null,
      });
      return analysis;
    } catch (err) {
      set({
        isLoadingAnalysis: false,
        analysisError: extractMeetingErrorMessage(err, 'Failed to load meeting analysis.'),
      });
      return null;
    }
  },

  triggerTranscription: async (meetingId: number) => {
    set({ isStartingTranscription: true, transcriptError: null });
    try {
      await startMeetingTranscription(meetingId);
      await get().loadMeetingById(meetingId, true);
      set({ isStartingTranscription: false });
    } catch (err) {
      set({
        isStartingTranscription: false,
        transcriptError: extractMeetingErrorMessage(err, 'Failed to start transcription.'),
      });
    }
  },

  triggerAnalysis: async (meetingId: number) => {
    const current = get().analysis;
    if (get().isStartingAnalysis || current?.status === 'processing') {
      return;
    }
    set({ isStartingAnalysis: true, analysisError: null });
    try {
      await startMeetingAnalysis(meetingId);
      const updated = await fetchMeetingAnalysis(meetingId);
      set({
        analysis: updated,
        isStartingAnalysis: false,
        analysisError: null,
      });
    } catch (err) {
      set({
        isStartingAnalysis: false,
        analysisError: extractMeetingErrorMessage(err, 'Failed to start meeting analysis.'),
      });
    }
  },

  removeMeeting: async (meetingId: number) => {
    set({ isDeletingId: meetingId, error: null });
    try {
      await deleteMeeting(meetingId);
      const currentSelected = get().selectedMeeting;
      set({
        selectedMeeting: currentSelected?.id === meetingId ? null : currentSelected,
        isDeletingId: null,
      });
      await get().loadMeetings();
    } catch (err) {
      const message = extractMeetingErrorMessage(err, 'Failed to delete meeting.');
      set({ isDeletingId: null, error: message });
      throw new Error(message);
    }
  },

  clearSelectedMeeting: () =>
    set({
      selectedMeeting: null,
      transcript: null,
      analysis: null,
      detailError: null,
      transcriptError: null,
      analysisError: null,
      isStartingTranscription: false,
      isStartingAnalysis: false,
    }),

  clearMeetings: () =>
    set({
      meetings: [],
      total: 0,
      selectedMeeting: null,
      transcript: null,
      analysis: null,
      isLoading: false,
      isLoadingDetail: false,
      isLoadingTranscript: false,
      isLoadingAnalysis: false,
      isStartingTranscription: false,
      isStartingAnalysis: false,
      isDeletingId: null,
      error: null,
      detailError: null,
      transcriptError: null,
      analysisError: null,
    }),

  clearError: () => set({ error: null }),
}));
