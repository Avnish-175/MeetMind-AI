import {
  AlertCircle,
  AlertTriangle,
  Brain,
  CalendarClock,
  CheckCircle2,
  CheckSquare,
  Clock,
  HelpCircle,
  Lightbulb,
  Loader2,
  RefreshCw,
  Sparkles,
  Tag,
  User,
} from 'lucide-react';
import type {
  BaseInsightItem,
  MeetingAnalysis,
} from '../../types/meeting';
import {
  formatTimestamp,
  getStatusBadgeInfo,
} from '../../utils/meetingFormat';

interface MeetingAnalysisSectionProps {
  analysis: MeetingAnalysis | null;
  hasUsableTranscript: boolean;
  isLoading: boolean;
  isStarting: boolean;
  error: string | null;
  onStartAnalysis: () => void;
  onJumpToSegment: (segmentId: number) => void;
}

function EvidenceBadges({
  item,
  onJumpToSegment,
}: {
  item: BaseInsightItem;
  onJumpToSegment: (segmentId: number) => void;
}) {
  const hasSegments = item.transcript_segment_ids && item.transcript_segment_ids.length > 0;
  const hasTimestamps = item.start_time !== null || item.end_time !== null;

  if (!hasSegments && !hasTimestamps) {
    return (
      <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
        No transcript evidence linked
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {hasTimestamps && (
        <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
          <Clock className="h-3 w-3 text-slate-400" />
          {formatTimestamp(item.start_time)}
          {item.end_time !== null ? ` – ${formatTimestamp(item.end_time)}` : ''}
        </span>
      )}
      {hasSegments &&
        item.transcript_segment_ids.map((segId) => (
          <button
            key={segId}
            type="button"
            onClick={() => onJumpToSegment(segId)}
            title={`Jump to transcript segment #${segId}`}
            className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200 transition-colors hover:bg-indigo-100"
          >
            Segment #{segId}
          </button>
        ))}
    </div>
  );
}

export function MeetingAnalysisSection({
  analysis,
  hasUsableTranscript,
  isLoading,
  isStarting,
  error,
  onStartAnalysis,
  onJumpToSegment,
}: MeetingAnalysisSectionProps) {
  const isProcessing =
    isStarting || analysis?.status === 'processing' || analysis?.status === 'pending';
  const statusBadge = analysis ? getStatusBadgeInfo(analysis.status) : null;

  return (
    <section className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
      {/* Header & Action */}
      <div className="flex flex-col gap-4 border-b border-slate-100 pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              <Sparkles className="h-4 w-4" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">
              Meeting Intelligence
            </h2>
            {statusBadge && (
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge.className}`}
              >
                {statusBadge.label}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Local NLP linguistic extraction and Ollama structured analysis grounded in
            transcript evidence.
            {analysis?.analysis_provider && analysis?.model_name && (
              <span className="ml-1.5 text-slate-400">
                • {analysis.analysis_provider} ({analysis.model_name})
              </span>
            )}
          </p>
        </div>

        <button
          type="button"
          onClick={onStartAnalysis}
          disabled={!hasUsableTranscript || isProcessing}
          className="inline-flex w-fit items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-xs transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-55"
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : analysis?.status === 'failed' ? (
            <>
              <RefreshCw className="h-4 w-4" />
              Retry Analysis
            </>
          ) : analysis?.status === 'completed' ? (
            <>
              <RefreshCw className="h-4 w-4" />
              Re-analyze Meeting
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Analyze Meeting
            </>
          )}
        </button>
      </div>

      {/* API / Request Error */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && !analysis ? (
        <div className="space-y-4">
          <div className="h-24 animate-pulse rounded-xl bg-slate-100" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="h-32 animate-pulse rounded-xl bg-slate-100" />
            <div className="h-32 animate-pulse rounded-xl bg-slate-100" />
          </div>
        </div>
      ) : isProcessing ? (
        /* Processing State */
        <div className="flex flex-col items-center justify-center rounded-xl border border-amber-200 bg-amber-50/70 px-6 py-10 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-amber-600" />
          <h3 className="mt-3 text-sm font-semibold text-slate-900">
            Analyzing meeting transcript...
          </h3>
          <p className="mt-1 max-w-md text-xs text-slate-600">
            Running local spaCy NLP extraction and Ollama structured reasoning. This page
            will automatically update as soon as results are ready.
          </p>
        </div>
      ) : analysis?.status === 'failed' ? (
        /* Failed State */
        <div className="flex flex-col gap-4 rounded-xl border border-rose-200 bg-rose-50 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
            <div>
              <h3 className="text-sm font-semibold text-rose-900">
                Meeting analysis failed
              </h3>
              <p className="mt-1 text-xs text-rose-700">
                {analysis.error_message ||
                  'An unexpected error occurred while analyzing this meeting.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onStartAnalysis}
            disabled={!hasUsableTranscript || isProcessing}
            className="inline-flex w-fit shrink-0 items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3.5 py-2 text-xs font-medium text-rose-700 transition-colors hover:bg-rose-100 disabled:opacity-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry Analysis
          </button>
        </div>
      ) : !analysis ? (
        /* Empty State */
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-12 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
            <Brain className="h-5 w-5" />
          </div>
          <h3 className="mt-3 text-sm font-semibold text-slate-900">
            No analysis generated yet
          </h3>
          <p className="mt-1 max-w-md text-xs text-slate-500">
            {hasUsableTranscript
              ? 'Click "Analyze Meeting" to extract a summary, key points, decisions, action items, deadlines, unresolved questions, and NLP insights.'
              : 'Transcribe this meeting first to generate timestamped segments before running meeting intelligence.'}
          </p>
        </div>
      ) : (
        /* Completed Analysis View */
        <div className="space-y-6">
          {/* 1. AI Summary */}
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <h3>AI Summary</h3>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-slate-700">
              {analysis.summary || 'No summary was generated for this meeting.'}
            </p>
          </div>

          {/* 2. Key Points & 3. Decisions */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Key Points */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <Lightbulb className="h-4 w-4 text-amber-500" />
                  <h3>Key Points</h3>
                </div>
                <span className="rounded-full bg-slate-200/70 px-2 py-0.5 text-xs font-medium text-slate-700">
                  {analysis.key_points.length}
                </span>
              </div>
              {analysis.key_points.length === 0 ? (
                <p className="mt-3 text-xs text-slate-500">
                  No key points extracted.
                </p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {analysis.key_points.map((point, idx) => (
                    <li
                      key={idx}
                      className="rounded-lg border border-slate-200/80 bg-white p-3.5"
                    >
                      <p className="text-sm text-slate-800">{point.text}</p>
                      <div className="mt-2.5">
                        <EvidenceBadges
                          item={point}
                          onJumpToSegment={onJumpToSegment}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Decisions */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <h3>Decisions</h3>
                </div>
                <span className="rounded-full bg-slate-200/70 px-2 py-0.5 text-xs font-medium text-slate-700">
                  {analysis.decisions.length}
                </span>
              </div>
              {analysis.decisions.length === 0 ? (
                <p className="mt-3 text-xs text-slate-500">
                  No explicit decisions identified.
                </p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {analysis.decisions.map((decision, idx) => (
                    <li
                      key={idx}
                      className="rounded-lg border border-slate-200/80 bg-white p-3.5"
                    >
                      <p className="text-sm font-medium text-slate-900">
                        {decision.text}
                      </p>
                      {decision.rationale && (
                        <p className="mt-1 text-xs text-slate-600">
                          Rationale: {decision.rationale}
                        </p>
                      )}
                      {decision.responsible_person && (
                        <p className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500">
                          <User className="h-3 w-3" />
                          {decision.responsible_person}
                        </p>
                      )}
                      <div className="mt-2.5">
                        <EvidenceBadges
                          item={decision}
                          onJumpToSegment={onJumpToSegment}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* 4. Action Items */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <CheckSquare className="h-4 w-4 text-indigo-600" />
                <h3>Action Items</h3>
              </div>
              <span className="rounded-full bg-slate-200/70 px-2 py-0.5 text-xs font-medium text-slate-700">
                {analysis.action_items.length}
              </span>
            </div>
            {analysis.action_items.length === 0 ? (
              <p className="mt-3 text-xs text-slate-500">
                No action items identified.
              </p>
            ) : (
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                {analysis.action_items.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col justify-between rounded-lg border border-slate-200/80 bg-white p-4"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-slate-900">
                          {item.text}
                        </p>
                        <span className="shrink-0 rounded-full bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-700 ring-1 ring-inset ring-sky-200">
                          Open
                        </span>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                        {item.responsible_person && (
                          <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5">
                            <User className="h-3 w-3 text-slate-500" />
                            {item.responsible_person}
                          </span>
                        )}
                        {item.due_date && (
                          <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5">
                            <CalendarClock className="h-3 w-3 text-slate-500" />
                            Due: {item.due_date}
                          </span>
                        )}
                        {item.priority && (
                          <span
                            className={`rounded px-2 py-0.5 font-medium capitalize ${
                              item.priority === 'high'
                                ? 'bg-rose-50 text-rose-700'
                                : item.priority === 'medium'
                                  ? 'bg-amber-50 text-amber-700'
                                  : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {item.priority} priority
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 border-t border-slate-100 pt-2.5">
                      <EvidenceBadges
                        item={item}
                        onJumpToSegment={onJumpToSegment}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 5. Deadlines & 6. Unresolved Questions */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Deadlines */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <CalendarClock className="h-4 w-4 text-rose-600" />
                  <h3>Deadlines</h3>
                </div>
                <span className="rounded-full bg-slate-200/70 px-2 py-0.5 text-xs font-medium text-slate-700">
                  {analysis.deadlines.length}
                </span>
              </div>
              {analysis.deadlines.length === 0 ? (
                <p className="mt-3 text-xs text-slate-500">
                  No explicit deadlines mentioned.
                </p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {analysis.deadlines.map((deadline, idx) => (
                    <li
                      key={idx}
                      className="rounded-lg border border-slate-200/80 bg-white p-3.5"
                    >
                      <p className="text-sm font-medium text-slate-900">
                        {deadline.text}
                      </p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                        {deadline.due_date && (
                          <span className="rounded bg-rose-50 px-2 py-0.5 font-medium text-rose-700">
                            Target: {deadline.due_date}
                          </span>
                        )}
                        {deadline.responsible_person && (
                          <span className="inline-flex items-center gap-1 text-slate-500">
                            <User className="h-3 w-3" />
                            {deadline.responsible_person}
                          </span>
                        )}
                      </div>
                      <div className="mt-2.5">
                        <EvidenceBadges
                          item={deadline}
                          onJumpToSegment={onJumpToSegment}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Unresolved Questions */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <HelpCircle className="h-4 w-4 text-violet-600" />
                  <h3>Unresolved Questions</h3>
                </div>
                <span className="rounded-full bg-slate-200/70 px-2 py-0.5 text-xs font-medium text-slate-700">
                  {analysis.unresolved_questions.length}
                </span>
              </div>
              {analysis.unresolved_questions.length === 0 ? (
                <p className="mt-3 text-xs text-slate-500">
                  No unresolved questions identified.
                </p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {analysis.unresolved_questions.map((question, idx) => (
                    <li
                      key={idx}
                      className="rounded-lg border border-slate-200/80 bg-white p-3.5"
                    >
                      <p className="text-sm text-slate-800">{question.text}</p>
                      {question.raised_by && (
                        <p className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500">
                          <User className="h-3 w-3" />
                          Raised by {question.raised_by}
                        </p>
                      )}
                      <div className="mt-2.5">
                        <EvidenceBadges
                          item={question}
                          onJumpToSegment={onJumpToSegment}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* 7. NLP Insights */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Brain className="h-4 w-4 text-indigo-600" />
                <h3>NLP Insights</h3>
              </div>
              {analysis.nlp_insights?.metadata && (
                <span className="rounded-md bg-slate-200/70 px-2.5 py-0.5 text-[11px] font-medium text-slate-700">
                  {analysis.nlp_insights.metadata.nlp_pipeline} •{' '}
                  {analysis.nlp_insights.metadata.total_sentences} sentences •{' '}
                  {analysis.nlp_insights.metadata.total_tokens} tokens
                </span>
              )}
            </div>

            {!analysis.nlp_insights ? (
              <p className="mt-3 text-xs text-slate-500">
                No NLP linguistic insights available for this analysis.
              </p>
            ) : (
              <div className="mt-4 space-y-4">
                {analysis.nlp_insights.metadata.warning && (
                  <div
                    role="status"
                    className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-800"
                  >
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    <span>{analysis.nlp_insights.metadata.warning}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  {/* Named Entities */}
                  <div className="rounded-lg border border-slate-200/80 bg-white p-4">
                    <h4 className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Named Entities ({analysis.nlp_insights.entities.length})
                    </h4>
                    {analysis.nlp_insights.entities.length === 0 ? (
                      <p className="mt-2 text-xs text-slate-500">
                        No named entities detected.
                      </p>
                    ) : (
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        {analysis.nlp_insights.entities.slice(0, 20).map((ent, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-800"
                          >
                            <span className="font-medium">{ent.text}</span>
                            <span className="rounded bg-indigo-100 px-1 py-0.2 text-[10px] font-semibold text-indigo-700">
                              {ent.label}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Keywords */}
                  <div className="rounded-lg border border-slate-200/80 bg-white p-4">
                    <h4 className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Top Keywords ({analysis.nlp_insights.keywords.length})
                    </h4>
                    {analysis.nlp_insights.keywords.length === 0 ? (
                      <p className="mt-2 text-xs text-slate-500">
                        No keywords extracted.
                      </p>
                    ) : (
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        {analysis.nlp_insights.keywords.map((kw, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700"
                          >
                            <Tag className="h-3 w-3" />
                            {kw.text}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Key Phrases */}
                  <div className="rounded-lg border border-slate-200/80 bg-white p-4">
                    <h4 className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                      Key Phrases ({analysis.nlp_insights.key_phrases.length})
                    </h4>
                    {analysis.nlp_insights.key_phrases.length === 0 ? (
                      <p className="mt-2 text-xs text-slate-500">
                        No key phrases extracted.
                      </p>
                    ) : (
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        {analysis.nlp_insights.key_phrases.map((phrase, idx) => (
                          <span
                            key={idx}
                            className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700"
                          >
                            {phrase}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
