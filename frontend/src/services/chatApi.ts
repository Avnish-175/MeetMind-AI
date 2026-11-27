import axios from 'axios';
import api from './api';
import type {
  ChatMessage,
  ChatMode,
  Conversation,
  ConversationDetail,
  ConversationListResponse,
  CreateConversationPayload,
  UpdateConversationPayload,
} from '../types/chat';

export async function fetchConversations(): Promise<ConversationListResponse> {
  const response = await api.get<ConversationListResponse>('/api/v1/chat/conversations');
  return response.data;
}

export async function fetchConversationById(id: number): Promise<ConversationDetail> {
  const response = await api.get<ConversationDetail>(`/api/v1/chat/conversations/${id}`);
  return response.data;
}

export async function createConversation(
  payload?: CreateConversationPayload
): Promise<Conversation> {
  const response = await api.post<Conversation>('/api/v1/chat/conversations', payload ?? {});
  return response.data;
}

export async function updateConversationTitle(
  id: number,
  payload: UpdateConversationPayload
): Promise<Conversation> {
  const response = await api.patch<Conversation>(`/api/v1/chat/conversations/${id}`, payload);
  return response.data;
}

export async function deleteConversation(id: number): Promise<void> {
  await api.delete(`/api/v1/chat/conversations/${id}`);
}

export async function sendChatMessage(
  conversationId: number,
  content: string,
  mode: ChatMode = 'general',
  meetingId: number | null = null
): Promise<ChatMessage> {
  const response = await api.post<ChatMessage>(
    `/api/v1/chat/conversations/${conversationId}/messages`,
    {
      content,
      mode,
      meeting_id: mode === 'meeting' ? meetingId : null,
    }
  );
  return response.data;
}

export function extractChatErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return (
        detail
          .map((d: { msg?: string }) => d.msg || '')
          .filter(Boolean)
          .join(', ') || fallback
      );
    }
  }
  return fallback;
}
