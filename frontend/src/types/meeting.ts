export type MeetingMediaType = 'audio' | 'video';

export type MeetingProcessingStatus =
  | 'uploaded'
  | 'processing'
  | 'transcribed'
  | 'completed'
  | 'failed'
  | (string & {});

export type EmbeddingStatus =
  | 'not_indexed'
  | 'pending'
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
  processing_error?: string | null;
  embedding_status?: EmbeddingStatus;
  embedding_error?: string | null;
  indexed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IndexingStartResponse {
  meeting_id: number;
  embedding_status: string;
  message: string;
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

export interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
}

export interface MeetingTranscript {
  id: number;
  meeting_id: number;
  full_text: string;
  language: string | null;
  language_probability: number | null;
  duration_seconds: number | null;
  model_name: string;
  segments: TranscriptSegment[];
  created_at: string;
  updated_at: string;
}

export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface BaseInsightItem {
  text: string;
  transcript_segment_ids: number[];
  start_time: number | null;
  end_time: number | null;
}

export type KeyPointItem = BaseInsightItem;

export interface DecisionItem extends BaseInsightItem {
  rationale: string | null;
  responsible_person: string | null;
}

export interface ActionItem extends BaseInsightItem {
  responsible_person: string | null;
  due_date: string | null;
  priority: 'low' | 'medium' | 'high' | null;
}

export interface DeadlineItem extends BaseInsightItem {
  due_date: string | null;
  responsible_person: string | null;
}

export interface UnresolvedQuestionItem extends BaseInsightItem {
  raised_by: string | null;
}

export interface ExtractedEntity {
  text: string;
  label: string;
  transcript_segment_ids: number[];
  start_time: number | null;
  end_time: number | null;
}

export interface ExtractedKeyword {
  text: string;
  score: number;
  transcript_segment_ids: number[];
}

export interface SentenceInsight {
  text: string;
  transcript_segment_id: number | null;
  start_time: number | null;
  end_time: number | null;
}

export interface LinguisticMetadata {
  total_tokens: number;
  total_sentences: number;
  unique_lemmas: number;
  entity_counts_by_type: Record<string, number>;
  topic_keywords: string[];
  nlp_pipeline: string;
  capabilities: string[];
  warning: string | null;
}

export interface TraditionalNLPResult {
  keywords: ExtractedKeyword[];
  entities: ExtractedEntity[];
  key_phrases: string[];
  sentences: SentenceInsight[];
  metadata: LinguisticMetadata;
}

export interface MeetingAnalysis {
  id: number;
  meeting_id: number;
  status: AnalysisStatus;
  summary: string | null;
  key_points: KeyPointItem[];
  decisions: DecisionItem[];
  action_items: ActionItem[];
  deadlines: DeadlineItem[];
  unresolved_questions: UnresolvedQuestionItem[];
  nlp_insights: TraditionalNLPResult | null;
  error_message: string | null;
  analysis_provider: string | null;
  model_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface StartAnalysisResponse {
  meeting_id: number;
  status: AnalysisStatus;
  message: string;
}
