import { Outlet } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { useAppStore } from '../../store/useAppStore';

export function MainLayout() {
  const { toggleSidebar } = useAppStore();

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur-xs lg:hidden">
          <button
            type="button"
            onClick={toggleSidebar}
            className="rounded-md p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold text-slate-900">MeetMind AI</span>
          <div className="w-9" />
        </header>

        <main className="flex-1 p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
