import { create } from 'zustand';
import {
  createConversation,
  deleteConversation,
  extractChatErrorMessage,
  fetchConversationById,
  fetchConversations,
  sendChatMessage,
  updateConversationTitle,
} from '../services/chatApi';
import type {
  ChatMessage,
  Conversation,
  ConversationDetail,
} from '../types/chat';

interface ChatState {
  conversations: Conversation[];
  activeConversationId: number | null;
  currentConversation: ConversationDetail | null;
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;
  isSendingMessage: boolean;
  isCreatingConversation: boolean;
  deletingConversationId: number | null;
  error: string | null;

  loadConversations: () => Promise<void>;
  selectConversation: (id: number) => Promise<void>;
  startNewConversation: (title?: string) => Promise<Conversation | null>;
  sendMessage: (content: string) => Promise<void>;
  updateTitle: (id: number, title: string) => Promise<void>;
  removeConversation: (id: number) => Promise<void>;
  clearActiveConversation: () => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  currentConversation: null,
  isLoadingConversations: false,
  isLoadingMessages: false,
  isSendingMessage: false,
  isCreatingConversation: false,
  deletingConversationId: null,
  error: null,

  loadConversations: async () => {
    set({ isLoadingConversations: true, error: null });
    try {
      const data = await fetchConversations();
      set({
        conversations: data.items,
        isLoadingConversations: false,
      });
    } catch (err) {
      set({
        isLoadingConversations: false,
        error: extractChatErrorMessage(err, 'Failed to load conversations.'),
      });
    }
  },

  selectConversation: async (id: number) => {
    if (get().activeConversationId === id && get().currentConversation?.id === id) {
      return;
    }
    set({
      activeConversationId: id,
      isLoadingMessages: true,
      error: null,
    });
    try {
      const detail = await fetchConversationById(id);
      set({
        currentConversation: detail,
        isLoadingMessages: false,
      });
    } catch (err) {
      set({
        isLoadingMessages: false,
        error: extractChatErrorMessage(err, 'Failed to load conversation messages.'),
      });
    }
  },

  startNewConversation: async (title?: string) => {
    set({ isCreatingConversation: true, error: null });
    try {
      const newConv = await createConversation({ title });
      const currentList = get().conversations;
      const detail: ConversationDetail = {
        ...newConv,
        messages: [],
      };
      set({
        conversations: [newConv, ...currentList],
        activeConversationId: newConv.id,
        currentConversation: detail,
        isCreatingConversation: false,
      });
      return newConv;
    } catch (err) {
      set({
        isCreatingConversation: false,
        error: extractChatErrorMessage(err, 'Failed to create a new conversation.'),
      });
      return null;
    }
  },

  sendMessage: async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    let targetId = get().activeConversationId;

    // If no active conversation, create one automatically
    if (!targetId) {
      const created = await get().startNewConversation();
      if (!created) {
        return;
      }
      targetId = created.id;
    }

    // Optimistically add user message to the UI
    const tempUserMsg: ChatMessage = {
      id: -Date.now(),
      conversation_id: targetId,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    const prevDetail = get().currentConversation;
    if (prevDetail && prevDetail.id === targetId) {
      set({
        currentConversation: {
          ...prevDetail,
          messages: [...prevDetail.messages, tempUserMsg],
        },
      });
    }

    set({ isSendingMessage: true, error: null });

    try {
      const assistantMsg = await sendChatMessage(targetId, trimmed);

      // Re-fetch conversation details to get synced messages from database
      const updatedDetail = await fetchConversationById(targetId);
      set({
        currentConversation: updatedDetail,
        isSendingMessage: false,
      });

      // Update conversation list to reflect new updated_at and possible title change
      const convList = await fetchConversations();
      set({ conversations: convList.items });
    } catch (err) {
      // Refresh current conversation from DB to ensure user message is visible even if assistant failed
      try {
        const synced = await fetchConversationById(targetId);
        set({ currentConversation: synced });
      } catch {
        // Fallback: keep current messages
      }

      set({
        isSendingMessage: false,
        error: extractChatErrorMessage(err, 'Failed to generate assistant response.'),
      });

      // Still update conversation list so the updated_at timestamp is fresh
      try {
        const convList = await fetchConversations();
        set({ conversations: convList.items });
      } catch {
        // Ignore background list refresh failure
      }
    }
  },

  updateTitle: async (id: number, title: string) => {
    try {
      const updated = await updateConversationTitle(id, { title });
      set((state) => ({
        conversations: state.conversations.map((c) => (c.id === id ? updated : c)),
        currentConversation:
          state.currentConversation?.id === id
            ? { ...state.currentConversation, title: updated.title }
            : state.currentConversation,
      }));
    } catch (err) {
      set({
        error: extractChatErrorMessage(err, 'Failed to rename conversation.'),
      });
    }
  },

  removeConversation: async (id: number) => {
    set({ deletingConversationId: id });
    try {
      await deleteConversation(id);
      set((state) => {
        const nextConversations = state.conversations.filter((c) => c.id !== id);
        const shouldResetCurrent = state.activeConversationId === id;
        return {
          conversations: nextConversations,
          activeConversationId: shouldResetCurrent ? null : state.activeConversationId,
          currentConversation: shouldResetCurrent ? null : state.currentConversation,
          deletingConversationId: null,
        };
      });
    } catch (err) {
      set({
        deletingConversationId: null,
        error: extractChatErrorMessage(err, 'Failed to delete conversation.'),
      });
    }
  },

  clearActiveConversation: () => {
    set({ activeConversationId: null, currentConversation: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));
