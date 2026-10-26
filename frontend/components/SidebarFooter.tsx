// ── SidebarFooter — Share / Save / Print actions ──────────────────────────
import { Share2, Bookmark, Printer } from 'lucide-react';

const ACTIONS = [
  { id: 'share-route',  Icon: Share2,   label: 'Share Route' },
  { id: 'save-trip',    Icon: Bookmark, label: 'Save to My Trips' },
  { id: 'print-route',  Icon: Printer,  label: 'Print' },
];

export function SidebarFooter() {
  return (
    <div className="mt-auto border-t border-gray-100 px-4 py-3 flex items-center justify-between">
      {ACTIONS.map(({ id, Icon, label }) => (
        <button
          key={id}
          id={id}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 font-medium transition-colors"
        >
          <Icon size={14} />
          {label}
        </button>
      ))}
    </div>
  );
}
