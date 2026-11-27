import { Route, Routes } from 'react-router-dom';
import {
  Bot,
  Calendar,
  CheckSquare,
  FileText,
  Settings,
} from 'lucide-react';
import { MainLayout } from '../components/layout/MainLayout';
import { PlaceholderPage } from '../components/common/PlaceholderPage';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { PublicOnlyRoute } from '../components/auth/PublicOnlyRoute';
import { LoginPage } from '../pages/auth/LoginPage';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { MeetingsPage } from '../pages/meetings/MeetingsPage';
import { MeetingDetailPage } from '../pages/meetings/MeetingDetailPage';
import { ChatPage } from '../pages/chat/ChatPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/meetings" element={<MeetingsPage />} />
        <Route path="/meetings/:meetingId" element={<MeetingDetailPage />} />
        <Route path="/chat" element={<ChatPage />} />
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
      </Route>
    </Routes>
  );
}
