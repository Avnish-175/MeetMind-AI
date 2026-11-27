import { create } from 'zustand';
import {
  deleteMeeting,
  extractMeetingErrorMessage,
  fetchMeetingById,
  fetchMeetings,
} from '../services/meetingApi';
import type { Meeting } from '../types/meeting';

interface MeetingState {
  meetings: Meeting[];
  total: number;
  selectedMeeting: Meeting | null;
  isLoading: boolean;
  isLoadingDetail: boolean;
  isDeletingId: number | null;
  error: string | null;
  detailError: string | null;
  loadMeetings: () => Promise<void>;
  loadMeetingById: (meetingId: number) => Promise<void>;
  removeMeeting: (meetingId: number) => Promise<void>;
  clearSelectedMeeting: () => void;
  clearMeetings: () => void;
  clearError: () => void;
}

export const useMeetingStore = create<MeetingState>((set, get) => ({
  meetings: [],
  total: 0,
  selectedMeeting: null,
  isLoading: false,
  isLoadingDetail: false,
  isDeletingId: null,
  error: null,
  detailError: null,

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

  loadMeetingById: async (meetingId: number) => {
    set({ isLoadingDetail: true, detailError: null, selectedMeeting: null });
    try {
      const meeting = await fetchMeetingById(meetingId);
      set({
        selectedMeeting: meeting,
        isLoadingDetail: false,
        detailError: null,
      });
    } catch (err) {
      set({
        selectedMeeting: null,
        isLoadingDetail: false,
        detailError: extractMeetingErrorMessage(err, 'Failed to load meeting details.'),
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

  clearSelectedMeeting: () => set({ selectedMeeting: null, detailError: null }),

  clearMeetings: () =>
    set({
      meetings: [],
      total: 0,
      selectedMeeting: null,
      isLoading: false,
      isLoadingDetail: false,
      isDeletingId: null,
      error: null,
      detailError: null,
    }),

  clearError: () => set({ error: null }),
}));
