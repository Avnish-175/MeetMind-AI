export type ChatMode = 'general' | 'meeting';

export interface CitationItem {
  meeting_id: number;
  meeting_title: string;
  chunk_index: number;
  start_time: number | null;
  end_time: number | null;
  segment_ids: number[];
  excerpt: string;
  similarity_score: number;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  mode?: ChatMode;
  meeting_id?: number | null;
  citations?: CitationItem[] | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
}

export interface CreateConversationPayload {
  title?: string;
}

export interface UpdateConversationPayload {
  title: string;
}

export interface SendMessagePayload {
  content: string;
  mode?: ChatMode;
  meeting_id?: number | null;
}
