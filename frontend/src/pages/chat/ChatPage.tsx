import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Check,
  Clock,
  Cpu,
  Database,
  Edit2,
  ExternalLink,
  FileText,
  Loader2,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
  User,
  Video,
  X,
} from 'lucide-react';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { useChatStore } from '../../store/useChatStore';
import { useMeetingStore } from '../../store/useMeetingStore';
import type { ChatMode, CitationItem } from '../../types/chat';
import { formatTimestamp } from '../../utils/meetingFormat';

const GENERAL_PROMPT_SUGGESTIONS = [
  'Help me structure an effective weekly project sync agenda.',
  'What are the key trade-offs of local AI vs cloud-hosted LLMs?',
  'Draft an email follow-up summarizing meeting decisions and next steps.',
];

const MEETING_PROMPT_SUGGESTIONS = [
  'What key decisions were made in my recent meetings?',
  'List all action items and deadlines discussed in the meeting.',
  'What open questions or blockers were left unresolved?',
];

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function formatCitationRange(citation: CitationItem): string {
  if (citation.start_time !== null && citation.end_time !== null) {
    return `${formatTimestamp(citation.start_time)} – ${formatTimestamp(citation.end_time)}`;
  }
  if (citation.start_time !== null) {
    return formatTimestamp(citation.start_time);
  }
  return 'Transcript excerpt';
}

export function ChatPage() {
  useDocumentTitle('AI Assistant');

  const {
    conversations,
    activeConversationId,
    currentConversation,
    chatMode,
    selectedMeetingId,
    isLoadingConversations,
    isLoadingMessages,
    isSendingMessage,
    isCreatingConversation,
    deletingConversationId,
    error,
    loadConversations,
    selectConversation,
    startNewConversation,
    setChatMode,
    setSelectedMeetingId,
    sendMessage,
    updateTitle,
    removeConversation,
    clearError,
  } = useChatStore();

  const {
    meetings,
    isStartingIndexing,
    indexingError,
    loadMeetings,
    triggerIndexing,
  } = useMeetingStore();

  const [inputMessage, setInputMessage] = useState('');
  const [editingTitleId, setEditingTitleId] = useState<number | null>(null);
  const [editingTitleValue, setEditingTitleValue] = useState('');
  const [showMobileList, setShowMobileList] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    void loadConversations();
    void loadMeetings();
  }, [loadConversations, loadMeetings]);

  // Poll meetings list if any meeting is currently indexing
  useEffect(() => {
    const hasIndexing = meetings.some(
      (m) => m.embedding_status === 'pending' || m.embedding_status === 'processing'
    );
    if (!hasIndexing) return;

    const intervalId = window.setInterval(() => {
      void loadMeetings();
    }, 3000);
    return () => window.clearInterval(intervalId);
  }, [meetings, loadMeetings]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages, isSendingMessage]);

  const selectedMeeting = useMemo(
    () => meetings.find((m) => m.id === selectedMeetingId) ?? null,
    [meetings, selectedMeetingId]
  );

  const indexedMeetingsCount = useMemo(
    () => meetings.filter((m) => m.embedding_status === 'completed').length,
    [meetings]
  );

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const text = inputMessage.trim();
    if (!text || isSendingMessage) return;

    setInputMessage('');
    setShowMobileList(false);
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSendMessage();
    }
  };

  const handleStartNewChat = async () => {
    setShowMobileList(false);
    await startNewConversation();
    textareaRef.current?.focus();
  };

  const handleSelectConversation = (id: number) => {
    setShowMobileList(false);
    void selectConversation(id);
  };

  const handleStartRename = (id: number, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingTitleId(id);
    setEditingTitleValue(currentTitle);
  };

  const handleSaveRename = async (id: number, e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = editingTitleValue.trim();
    if (trimmed) {
      await updateTitle(id, trimmed);
    }
    setEditingTitleId(null);
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirmDeleteId === id) {
      await removeConversation(id);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(id);
    }
  };

  const handleSuggestionClick = (prompt: string) => {
    setInputMessage(prompt);
    textareaRef.current?.focus();
  };

  const handleModeChange = (mode: ChatMode) => {
    setChatMode(mode);
  };

  const promptSuggestions =
    chatMode === 'meeting' ? MEETING_PROMPT_SUGGESTIONS : GENERAL_PROMPT_SUGGESTIONS;

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            AI Assistant
          </h1>
          <p className="text-sm text-slate-500">
            General AI chat and meeting-aware Q&amp;A running locally on your hardware.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <Cpu className="h-3 w-3" />
            qwen2.5:1.5b (Local Ollama)
          </span>
        </div>
      </div>

      {/* Main Chat Layout Container */}
      <div className="relative flex h-[calc(100vh-13.5rem)] min-h-[540px] overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-xs">
        {/* Left Sidebar: Conversations List */}
        <aside
          className={`absolute inset-y-0 left-0 z-20 flex w-full flex-col border-r border-slate-200 bg-slate-50/80 transition-transform duration-200 ease-in-out md:static md:w-80 md:translate-x-0 ${
            showMobileList ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          }`}
        >
          {/* Sidebar Top: New Chat Button */}
          <div className="flex items-center justify-between border-b border-slate-200 p-3">
            <button
              type="button"
              onClick={handleStartNewChat}
              disabled={isCreatingConversation}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-xs transition hover:bg-indigo-500 disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              <span>{isCreatingConversation ? 'Creating...' : 'New Chat'}</span>
            </button>
            <button
              type="button"
              onClick={() => setShowMobileList(false)}
              className="ml-2 rounded-lg p-2 text-slate-400 hover:bg-slate-200 hover:text-slate-700 md:hidden"
              aria-label="Close conversation list"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Sidebar Conversations Scroll Area */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {isLoadingConversations && conversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <RefreshCw className="h-5 w-5 animate-spin" />
                <span className="mt-2 text-xs">Loading conversations...</span>
              </div>
            ) : conversations.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <MessageSquare className="mx-auto h-8 w-8 stroke-1 text-slate-300" />
                <p className="mt-2 text-xs font-medium text-slate-500">
                  No conversations yet
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Start a new conversation to begin.
                </p>
              </div>
            ) : (
              conversations.map((conv) => {
                const isActive = conv.id === activeConversationId;
                const isDeleting = deletingConversationId === conv.id;
                const isEditing = editingTitleId === conv.id;
                const isConfirming = confirmDeleteId === conv.id;

                return (
                  <div
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={`group relative flex cursor-pointer items-center justify-between rounded-xl px-3 py-2.5 text-sm transition ${
                      isActive
                        ? 'bg-indigo-50/90 text-indigo-900 font-medium shadow-2xs'
                        : 'text-slate-700 hover:bg-slate-100/90 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex min-w-0 flex-1 items-center gap-2.5">
                      <MessageSquare
                        className={`h-4 w-4 shrink-0 ${
                          isActive ? 'text-indigo-600' : 'text-slate-400'
                        }`}
                      />

                      {isEditing ? (
                        <form
                          onSubmit={(e) => void handleSaveRename(conv.id, e)}
                          className="flex min-w-0 flex-1 items-center gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="text"
                            value={editingTitleValue}
                            onChange={(e) => setEditingTitleValue(e.target.value)}
                            onBlur={() => void handleSaveRename(conv.id)}
                            autoFocus
                            className="w-full rounded border border-indigo-400 bg-white px-1.5 py-0.5 text-xs text-slate-900 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
                          />
                          <button
                            type="submit"
                            className="rounded p-1 text-emerald-600 hover:bg-emerald-50"
                          >
                            <Check className="h-3 w-3" />
                          </button>
                        </form>
                      ) : (
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium leading-snug">
                            {conv.title}
                          </p>
                          <p className="truncate text-[10px] text-slate-400">
                            {formatTime(conv.updated_at)}
                          </p>
                        </div>
                      )}
                    </div>

                    {!isEditing && (
                      <div className="ml-1 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 md:opacity-0 focus-within:opacity-100">
                        <button
                          type="button"
                          onClick={(e) => handleStartRename(conv.id, conv.title, e)}
                          className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
                          title="Rename conversation"
                        >
                          <Edit2 className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => void handleDeleteConversation(conv.id, e)}
                          disabled={isDeleting}
                          className={`rounded p-1 transition ${
                            isConfirming
                              ? 'bg-rose-100 text-rose-600 font-bold text-[10px] px-1.5'
                              : 'text-slate-400 hover:bg-rose-50 hover:text-rose-600'
                          }`}
                          title={isConfirming ? 'Click again to confirm' : 'Delete conversation'}
                        >
                          {isConfirming ? 'Delete?' : <Trash2 className="h-3 w-3" />}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Right Main Chat Area */}
        <section className="flex flex-1 flex-col min-w-0 bg-white">
          {/* Chat Area Top Bar + Mode Selector */}
          <div className="flex flex-col gap-2 border-b border-slate-200 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <button
                type="button"
                onClick={() => setShowMobileList(true)}
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 md:hidden"
                aria-label="View conversations"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <h2 className="truncate text-sm font-semibold text-slate-800">
                    {currentConversation ? currentConversation.title : 'New Chat'}
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    {currentConversation
                      ? `${currentConversation.messages.length} messages`
                      : 'Local intelligence session'}
                  </p>
                </div>
              </div>
            </div>

            {/* Mode Selector */}
            <div className="flex items-center gap-1 self-start rounded-xl bg-slate-100 p-1 sm:self-auto">
              <button
                type="button"
                onClick={() => handleModeChange('general')}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  chatMode === 'general'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
                General Chat
              </button>
              <button
                type="button"
                onClick={() => handleModeChange('meeting')}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  chatMode === 'meeting'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Video className="h-3.5 w-3.5 text-indigo-600" />
                Meeting Chat
              </button>
            </div>
          </div>

          {/* Meeting Context Bar (shown in Meeting Chat mode) */}
          {chatMode === 'meeting' && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-indigo-100 bg-indigo-50/40 px-4 py-2 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-slate-700">Search scope:</span>
                <select
                  value={selectedMeetingId ?? ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedMeetingId(val ? Number(val) : null);
                  }}
                  className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-800 shadow-2xs focus:border-indigo-500 focus:outline-hidden"
                >
                  <option value="">
                    All My Indexed Meetings ({indexedMeetingsCount})
                  </option>
                  {meetings.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.title}{' '}
                      {m.embedding_status === 'completed'
                        ? '(Indexed)'
                        : m.embedding_status === 'processing' || m.embedding_status === 'pending'
                        ? '(Indexing...)'
                        : '(Not indexed)'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selected Meeting Indexing Status / Action */}
              {selectedMeeting && (
                <div className="flex items-center gap-2">
                  {selectedMeeting.embedding_status === 'completed' ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                      <Check className="h-3 w-3" />
                      Indexed
                    </span>
                  ) : selectedMeeting.embedding_status === 'pending' ||
                    selectedMeeting.embedding_status === 'processing' ||
                    isStartingIndexing ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Indexing...
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => void triggerIndexing(selectedMeeting.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-indigo-200 bg-white px-2.5 py-1 text-[11px] font-medium text-indigo-700 shadow-2xs hover:bg-indigo-50"
                    >
                      <Database className="h-3 w-3" />
                      Index Meeting
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {indexingError && chatMode === 'meeting' && (
            <div className="mx-4 mt-2 flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 ring-1 ring-inset ring-rose-600/20">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              <span>{indexingError}</span>
            </div>
          )}

          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            {isLoadingMessages ? (
              <div className="flex h-full items-center justify-center text-slate-400">
                <RefreshCw className="h-6 w-6 animate-spin" />
              </div>
            ) : !currentConversation || currentConversation.messages.length === 0 ? (
              <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 shadow-xs ring-1 ring-indigo-500/20">
                  {chatMode === 'meeting' ? (
                    <Video className="h-6 w-6" />
                  ) : (
                    <Sparkles className="h-6 w-6" />
                  )}
                </div>
                <h3 className="mt-4 text-base font-semibold text-slate-900">
                  {chatMode === 'meeting'
                    ? 'Ask questions about your meetings'
                    : 'How can MeetMind help you today?'}
                </h3>
                <p className="mt-1 text-xs text-slate-500 max-w-md">
                  {chatMode === 'meeting'
                    ? selectedMeeting
                      ? `Searching transcripts from "${selectedMeeting.title}". Answers are strictly grounded with citations.`
                      : `Searching across ${indexedMeetingsCount} indexed meeting(s). Answers include timestamped transcript citations.`
                    : 'Ask questions, draft notes, organize meeting plans, or brainstorm. All conversations remain strictly on your local device.'}
                </p>

                <div className="mt-6 grid w-full gap-2 text-left">
                  {promptSuggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 text-xs text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50/30 hover:text-indigo-900"
                    >
                      💡 {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {currentConversation.messages.map((msg, index) => {
                  const isUser = msg.role === 'user';
                  const hasCitations =
                    !isUser && Array.isArray(msg.citations) && msg.citations.length > 0;

                  return (
                    <div
                      key={msg.id || `msg-${index}`}
                      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                    >
                      {!isUser && (
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-indigo-400 shadow-xs">
                          <Bot className="h-4 w-4" />
                        </div>
                      )}

                      <div className={`max-w-[85%] sm:max-w-[75%] space-y-2`}>
                        <div
                          className={`group relative rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                            isUser
                              ? 'bg-indigo-600 text-white rounded-br-xs shadow-xs'
                              : 'bg-slate-100 text-slate-800 rounded-bl-xs border border-slate-200/80 shadow-2xs'
                          }`}
                        >
                          {msg.mode === 'meeting' && (
                            <div
                              className={`mb-1.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                isUser
                                  ? 'bg-indigo-500/60 text-indigo-100'
                                  : 'bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-600/15'
                              }`}
                            >
                              <Video className="h-2.5 w-2.5" />
                              Meeting RAG
                            </div>
                          )}
                          <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                          {msg.created_at && (
                            <div
                              className={`mt-1.5 text-[10px] ${
                                isUser ? 'text-indigo-200 text-right' : 'text-slate-400'
                              }`}
                            >
                              {formatTime(msg.created_at)}
                            </div>
                          )}
                        </div>

                        {/* Source Citations */}
                        {hasCitations && (
                          <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-3 space-y-2">
                            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                              <FileText className="h-3.5 w-3.5 text-indigo-600" />
                              Sources ({msg.citations!.length})
                            </div>
                            <div className="grid gap-2">
                              {msg.citations!.map((citation, cIdx) => {
                                const firstSegId =
                                  citation.segment_ids && citation.segment_ids.length > 0
                                    ? citation.segment_ids[0]
                                    : null;
                                const targetUrl =
                                  firstSegId !== null
                                    ? `/meetings/${citation.meeting_id}?segment=${firstSegId}`
                                    : `/meetings/${citation.meeting_id}`;

                                return (
                                  <Link
                                    key={`${citation.meeting_id}-${citation.chunk_index}-${cIdx}`}
                                    to={targetUrl}
                                    className="block rounded-lg border border-slate-200 bg-white p-2.5 transition hover:border-indigo-300 hover:bg-indigo-50/20"
                                  >
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="truncate text-xs font-semibold text-slate-800">
                                        {citation.meeting_title}
                                      </span>
                                      <span className="inline-flex shrink-0 items-center gap-1 text-[11px] font-medium text-indigo-600">
                                        <Clock className="h-3 w-3" />
                                        {formatCitationRange(citation)}
                                        <ExternalLink className="h-3 w-3" />
                                      </span>
                                    </div>
                                    <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-600">
                                      &ldquo;{citation.excerpt}&rdquo;
                                    </p>
                                  </Link>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>

                      {isUser && (
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
                          <User className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Assistant Generating State */}
                {isSendingMessage && (
                  <div className="flex gap-3 justify-start items-center">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-indigo-400 shadow-xs animate-pulse">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="rounded-2xl rounded-bl-xs border border-slate-200/80 bg-slate-100 px-4 py-3 text-sm text-slate-600 shadow-2xs flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-indigo-600 animate-spin" />
                      <span className="text-xs font-medium">
                        {chatMode === 'meeting'
                          ? 'Searching meeting transcripts & generating grounded answer...'
                          : 'MeetMind is thinking...'}
                      </span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mx-4 mb-2 flex items-center justify-between rounded-xl bg-rose-50 px-3.5 py-2.5 text-xs text-rose-700 ring-1 ring-inset ring-rose-600/20">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
                <span>{error}</span>
              </div>
              <button
                type="button"
                onClick={clearError}
                className="rounded-md p-1 hover:bg-rose-100 text-rose-600"
                aria-label="Dismiss error"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {/* Message Input Form */}
          <div className="border-t border-slate-200 p-3 md:p-4 bg-slate-50/50">
            <form onSubmit={(e) => void handleSendMessage(e)} className="relative">
              <textarea
                ref={textareaRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                disabled={isSendingMessage}
                placeholder={
                  chatMode === 'meeting'
                    ? selectedMeeting
                      ? `Ask about "${selectedMeeting.title}"... (Enter to send)`
                      : 'Ask across your indexed meetings... (Enter to send)'
                    : 'Ask MeetMind anything... (Press Enter to send, Shift+Enter for new line)'
                }
                className="w-full resize-none rounded-xl border border-slate-300 bg-white p-3 pr-14 text-sm text-slate-800 placeholder-slate-400 shadow-2xs transition focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isSendingMessage}
                className="absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-xs transition hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600"
                aria-label="Send message"
              >
                {isSendingMessage ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </form>
            <div className="mt-1 flex items-center justify-between px-1 text-[11px] text-slate-400">
              <span>
                {chatMode === 'meeting'
                  ? 'Meeting-Aware RAG • pgvector + Local Ollama'
                  : 'Local Ollama • Privacy-First'}
              </span>
              <span className="hidden sm:inline">Enter to send • Shift+Enter for new line</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
