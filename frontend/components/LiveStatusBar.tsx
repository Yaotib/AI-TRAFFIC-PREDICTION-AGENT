// ── LiveStatusBar — bottom map status bar ─────────────────────────────────
import { formatDistanceToNow } from '../lib/dateUtils';
import { useRouteStore } from '../lib/store';

export function LiveStatusBar() {
  const liveGpsLocked = useRouteStore((s) => s.liveGpsLocked);
  const lastUpdated   = useRouteStore((s) => s.lastUpdated);

  const updatedAgo = lastUpdated
    ? formatDistanceToNow(lastUpdated)
    : 'no updates yet';

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 bg-white/95 backdrop-blur-sm rounded-full px-5 py-2 flex items-center gap-3 shadow-md border border-gray-100 text-xs font-medium text-gray-600 whitespace-nowrap">
      {/* GPS dot */}
      <span className="flex items-center gap-1.5">
        <span
          className={[
            'w-2 h-2 rounded-full animate-pulse-dot',
            liveGpsLocked ? 'bg-emerald-500' : 'bg-gray-400',
          ].join(' ')}
        />
        {liveGpsLocked ? 'GPS connected' : 'GPS status unavailable'}
      </span>

      <span className="text-gray-300">|</span>

      <span className="text-gray-400">Updated {updatedAgo}</span>
    </div>
  );
}
