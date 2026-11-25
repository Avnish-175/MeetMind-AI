import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Video,
  Bot,
  Calendar,
  CheckSquare,
  FileText,
  Settings,
  X,
  Sparkles,
  LogOut,
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { useAuthStore } from '../../store/useAuthStore';

const navItems = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'Meetings', to: '/meetings', icon: Video },
  { label: 'AI Assistant', to: '/chat', icon: Bot },
  { label: 'Calendar', to: '/calendar', icon: Calendar },
  { label: 'Tasks', to: '/tasks', icon: CheckSquare },
  { label: 'Notes', to: '/notes', icon: FileText },
  { label: 'Settings', to: '/settings', icon: Settings },
];

export function Sidebar() {
  const navigate = useNavigate();
  const { isSidebarOpen, setSidebarOpen } = useAppStore();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    setSidebarOpen(false);
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <>
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/50 backdrop-blur-xs lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-900 text-slate-100 transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500 text-white shadow-sm">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <span className="block text-sm font-semibold tracking-tight text-white">
                MeetMind AI
              </span>
              <span className="block text-[11px] text-slate-400">
                Understand. Organize. Act.
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-slate-800 p-4 space-y-3">
          {user && (
            <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-800/60 px-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-slate-100">
                  {user.full_name}
                </p>
                <p className="truncate text-[11px] text-slate-400">
                  {user.email}
                </p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                title="Sign out"
                aria-label="Sign out"
                className="shrink-0 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
          <div className="rounded-lg bg-slate-800/40 px-3 py-2">
            <p className="text-xs font-medium text-slate-300">Local-First Workspace</p>
            <p className="mt-0.5 text-[11px] text-slate-400">v0.1.0 • Foundation</p>
          </div>
        </div>
      </aside>
    </>
  );
}
