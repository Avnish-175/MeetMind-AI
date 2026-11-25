import type { LucideIcon } from 'lucide-react';
import { Clock } from 'lucide-react';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

export function PlaceholderPage({ title, description, icon: Icon }: PlaceholderPageProps) {
  useDocumentTitle(title);

  return (
    <div className="mx-auto max-w-4xl py-12">
      <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
          <Icon className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-600">{description}</p>
        <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-1.5 text-xs font-medium text-slate-600">
          <Clock className="h-3.5 w-3.5 text-indigo-500" />
          Module Planned — Coming in a future phase
        </div>
      </div>
    </div>
  );
}
