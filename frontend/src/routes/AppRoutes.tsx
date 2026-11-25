import { Route, Routes } from 'react-router-dom';
import {
  Video,
  Bot,
  Calendar,
  CheckSquare,
  FileText,
  Settings,
} from 'lucide-react';
import { MainLayout } from '../components/layout/MainLayout';
import { PlaceholderPage } from '../components/common/PlaceholderPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route
          path="/meetings"
          element={
            <PlaceholderPage
              title="Meetings"
              description="Upload, record, transcribe, and review multimodal meeting sessions."
              icon={Video}
            />
          }
        />
        <Route
          path="/chat"
          element={
            <PlaceholderPage
              title="AI Assistant"
              description="Ask questions across your local meeting history, transcripts, and action items."
              icon={Bot}
            />
          }
        />
        <Route
          path="/calendar"
          element={
            <PlaceholderPage
              title="Calendar"
              description="View upcoming scheduled meetings and sync local recording reminders."
              icon={Calendar}
            />
          }
        />
        <Route
          path="/tasks"
          element={
            <PlaceholderPage
              title="Tasks"
              description="Track and manage action items automatically extracted from your meetings."
              icon={CheckSquare}
            />
          }
        />
        <Route
          path="/notes"
          element={
            <PlaceholderPage
              title="Notes"
              description="Organize structured meeting summaries, key decisions, and personal notes."
              icon={FileText}
            />
          }
        />
        <Route
          path="/settings"
          element={
            <PlaceholderPage
              title="Settings"
              description="Configure local-first storage paths, AI model preferences, and application behavior."
              icon={Settings}
            />
          }
        />
      </Route>
    </Routes>
  );
}
