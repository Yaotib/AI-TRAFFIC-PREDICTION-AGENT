
import { Clock, ChevronDown } from 'lucide-react';
import { useRouteStore } from '../lib/store';

function formatClock(value: string | null | undefined): string {
  if (!value) return 'Not available';

  const timePart = value.includes('T')
    ? value.split('T')[1].slice(0, 5)
    : value.slice(0, 5);

  const [hoursText, minutes] = timePart.split(':');
  const hours = Number(hoursText);

  if (!Number.isFinite(hours) || !minutes) return value;

  return `${hours % 12 || 12}:${minutes} ${hours >= 12 ? 'PM' : 'AM'}`;
}

export function TopBar() {
  const planningResult = useRouteStore((s) => s.planningResult);
  const recommended = planningResult?.recommended;

  const departureTime = recommended
    ? formatClock(recommended.departure_local)
    : 'Not planned';

  const arrival = recommended
    ? formatClock(recommended.arrival_local)
    : 'Not available';

  return (
    <header className="h-14 border-b border-gray-100 bg-white flex items-center justify-between px-5 shrink-0 z-20 shadow-sm">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl bg-brand-700 flex items-center justify-center shadow-sm">
          <svg
            width="18"
            height="18"
            viewBox="0 0 18 18"
            fill="none"
            aria-hidden="true"
          >
            <circle
              cx="9"
              cy="9"
              r="7"
              stroke="white"
              strokeWidth="1.8"
            />
            <path
              d="M9 5v4l2.5 2.5"
              stroke="white"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <span className="font-extrabold text-gray-900 text-base tracking-tight">
          MetroRoute
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-200"
          aria-label={`Recommended departure: ${departureTime}`}
        >
          <Clock size={13} className="text-gray-500" />
          <span className="text-xs text-gray-600 font-medium">
            Departure:
          </span>
          <span className="text-xs font-bold text-gray-900">
            {departureTime}
          </span>
          <ChevronDown size={13} className="text-gray-400" />
        </div>

        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-50 border border-brand-200">
          <span className="text-xs text-brand-700 font-medium">
            Est. Arrival
          </span>
          <span className="text-xs font-bold text-brand-800">
            {arrival}
          </span>
        </div>
      </div>
    </header>
  );
}
