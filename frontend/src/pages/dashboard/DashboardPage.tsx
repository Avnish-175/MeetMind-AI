import { useNavigate } from 'react-router-dom';
import {
  Video,
  CheckSquare,
  Clock,
  Sparkles,
  Plus,
  Bot,
  Calendar,
  ArrowRight,
  Users,
} from 'lucide-react';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import type { CalendarEvent, MeetingSummary, TaskItem } from '../../types';

const overviewStats = [
  { label: 'Meetings This Week', value: '12', change: '+3 from last week', icon: Video },
  { label: 'Open Action Items', value: '8', change: '4 due this week', icon: CheckSquare },
  { label: 'Hours Transcribed', value: '14.5h', change: 'Local-first storage', icon: Clock },
  { label: 'AI Summaries Ready', value: '10', change: '100% processed locally', icon: Sparkles },
];

const recentMeetings: MeetingSummary[] = [
  {
    id: 'm-1',
    title: 'Q4 Product Roadmap & Architecture Sync',
    date: 'Today, 10:00 AM',
    duration: '45 min',
    participants: 6,
    status: 'Processed',
  },
  {
    id: 'm-2',
    title: 'Engineering Sprint Planning',
    date: 'Yesterday, 2:30 PM',
    duration: '60 min',
    participants: 8,
    status: 'Processed',
  },
  {
    id: 'm-3',
    title: 'Design System & UX Review',
    date: 'Nov 23, 11:00 AM',
    duration: '30 min',
    participants: 4,
    status: 'Processed',
  },
];

const upcomingTasks: TaskItem[] = [
  {
    id: 't-1',
    title: 'Finalize API contract for audio ingestion',
    dueDate: 'Tomorrow',
    priority: 'High',
    sourceMeeting: 'Q4 Product Roadmap & Architecture Sync',
    completed: false,
  },
  {
    id: 't-2',
    title: 'Share updated sprint velocity metrics',
    dueDate: 'Nov 28',
    priority: 'Medium',
    sourceMeeting: 'Engineering Sprint Planning',
    completed: false,
  },
  {
    id: 't-3',
    title: 'Review sidebar navigation accessibility',
    dueDate: 'Nov 29',
    priority: 'Low',
    sourceMeeting: 'Design System & UX Review',
    completed: false,
  },
];

const upcomingEvents: CalendarEvent[] = [
  {
    id: 'e-1',
    title: 'Weekly AI Pipeline Check-in',
    time: 'Tomorrow, 9:30 AM – 10:15 AM',
    platform: 'Local Recording',
    attendees: 5,
  },
  {
    id: 'e-2',
    title: 'Customer Feedback Synthesis',
    time: 'Nov 27, 3:00 PM – 3:45 PM',
    platform: 'Zoom',
    attendees: 4,
  },
];

export function DashboardPage() {
  useDocumentTitle('Dashboard');
  const navigate = useNavigate();

  return (
    <div className="space-y-8">
      {/* Welcome Heading & Quick Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Welcome back to MeetMind AI
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Understand. Organize. Act. Here is a snapshot of your workspace.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => navigate('/meetings')}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-xs transition-colors hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            New Meeting
          </button>
          <button
            type="button"
            onClick={() => navigate('/chat')}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-xs transition-colors hover:bg-slate-50"
          >
            <Bot className="h-4 w-4 text-indigo-600" />
            Ask AI Assistant
          </button>
        </div>
      </div>

      {/* Overview Statistic Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {overviewStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-600">{stat.label}</span>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <p className="mt-3 text-2xl font-semibold text-slate-900">{stat.value}</p>
              <p className="mt-1 text-xs text-slate-500">{stat.change}</p>
            </div>
          );
        })}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent Meetings (2 columns wide on lg) */}
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Recent Meetings</h2>
            <button
              type="button"
              onClick={() => navigate('/meetings')}
              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
            >
              View all <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="divide-y divide-slate-100">
            {recentMeetings.map((meeting) => (
              <div
                key={meeting.id}
                className="flex flex-col gap-2 py-3.5 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">{meeting.title}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span>{meeting.date}</span>
                    <span>•</span>
                    <span>{meeting.duration}</span>
                    <span>•</span>
                    <span className="inline-flex items-center gap-1">
                      <Users className="h-3 w-3" /> {meeting.participants}
                    </span>
                  </div>
                </div>
                <span className="inline-flex w-fit items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                  {meeting.status}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Upcoming Events */}
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Upcoming Events</h2>
            <button
              type="button"
              onClick={() => navigate('/calendar')}
              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
            >
              Calendar <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="space-y-3">
            {upcomingEvents.map((event) => (
              <div
                key={event.id}
                className="rounded-lg border border-slate-100 bg-slate-50/70 p-3.5"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-indigo-100 text-indigo-600">
                    <Calendar className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">{event.title}</p>
                    <p className="mt-0.5 text-xs text-slate-600">{event.time}</p>
                    <p className="mt-1 text-[11px] text-slate-500">
                      {event.platform} • {event.attendees} attendees
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Upcoming Tasks */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Upcoming Tasks</h2>
          <button
            type="button"
            onClick={() => navigate('/tasks')}
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
          >
            View tasks <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="divide-y divide-slate-100">
          {upcomingTasks.map((task) => (
            <div
              key={task.id}
              className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex items-start gap-3">
                <CheckSquare className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                <div>
                  <p className="text-sm font-medium text-slate-900">{task.title}</p>
                  <p className="text-xs text-slate-500">From: {task.sourceMeeting}</p>
                </div>
              </div>
              <div className="flex items-center gap-2.5 pl-7 sm:pl-0">
                <span className="text-xs text-slate-500">Due {task.dueDate}</span>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    task.priority === 'High'
                      ? 'bg-rose-50 text-rose-700'
                      : task.priority === 'Medium'
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {task.priority}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
