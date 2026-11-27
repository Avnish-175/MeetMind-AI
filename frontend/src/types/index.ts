export type {
  ActionItem,
  AnalysisStatus,
  DeadlineItem,
  DecisionItem,
  EmbeddingStatus,
  ExtractedEntity,
  ExtractedKeyword,
  IndexingStartResponse,
  KeyPointItem,
  LinguisticMetadata,
  Meeting,
  MeetingAnalysis,
  MeetingListResponse,
  MeetingMediaType,
  MeetingProcessingStatus,
  MeetingTranscript,
  StartAnalysisResponse,
  TraditionalNLPResult,
  TranscriptSegment,
  UnresolvedQuestionItem,
  UploadMeetingPayload,
} from './meeting';

export type {
  ChatMessage,
  ChatMode,
  CitationItem,
  Conversation,
  ConversationDetail,
  ConversationListResponse,
  CreateConversationPayload,
  SendMessagePayload,
  UpdateConversationPayload,
} from './chat';

export interface MeetingSummary {
  id: string;
  title: string;
  date: string;
  duration: string;
  participants: number;
  status: 'Processed' | 'Scheduled' | 'Draft';
}

export interface TaskItem {
  id: string;
  title: string;
  dueDate: string;
  priority: 'High' | 'Medium' | 'Low';
  sourceMeeting: string;
  completed: boolean;
}

export interface CalendarEvent {
  id: string;
  title: string;
  time: string;
  platform: string;
  attendees: number;
}
