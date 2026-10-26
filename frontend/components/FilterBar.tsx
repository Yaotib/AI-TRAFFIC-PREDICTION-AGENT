// ── FilterBar — Fastest / Avoid Tolls / Scenic Route / Add stop ────────────
import { Plus } from 'lucide-react';
import { useRouteStore } from '../lib/store';
import type { RouteState } from '../lib/types';

type Filter = RouteState['activeFilter'];

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'fastest',  label: 'Fastest' },
  { id: 'no-tolls', label: 'Avoid Tolls' },
  { id: 'scenic',   label: 'Scenic Route' },
];

export function FilterBar() {
  const active    = useRouteStore((s) => s.activeFilter);
  const setFilter = useRouteStore((s) => s.setActiveFilter);

  return (
    <div className="px-4 pb-3 flex items-center gap-2 flex-wrap">
      {FILTERS.map(({ id, label }) => (
        <button
          key={id}
          id={`filter-${id}`}
          onClick={() => setFilter(id)}
          className={[
            'px-3 py-1.5 rounded-full text-xs font-semibold transition-all',
            active === id
              ? 'bg-brand-900 text-white shadow-sm'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
          ].join(' ')}
        >
          {label}
        </button>
      ))}
      <button
        id="add-stop-btn"
        className="px-3 py-1.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all flex items-center gap-1"
      >
        <Plus size={12} /> Add stop
      </button>
    </div>
  );
}
