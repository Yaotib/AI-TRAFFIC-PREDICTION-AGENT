// ── RouteCard — recommended route detail card ──────────────────────────────
import { ArrowRight, Navigation } from 'lucide-react';
import { useRouteStore } from '../lib/store';
import { TrafficBadge } from './TrafficBadge';

export function RouteCard() {
  const routeOptions   = useRouteStore((s) => s.routeOptions);
  const selectedId     = useRouteStore((s) => s.selectedRouteId);
  const turns          = useRouteStore((s) => s.turnInstructions);
  const startNav       = useRouteStore((s) => s.startNavigation);
  const departureTime  = useRouteStore((s) => s.departureTime);
  const arrival        = useRouteStore((s) => s.estimatedArrival);
  const isNavigating   = useRouteStore((s) => s.isNavigating);

  const route = routeOptions.find((r) => r.id === selectedId) ?? routeOptions[0];
  if (!route) return null;

  const firstTurn = turns[0];

  return (
    <div
      id="recommended-route-card"
      className="mx-3 mb-3 rounded-[12px] border-2 border-brand-600 bg-white shadow-sm animate-slide-up overflow-hidden"
    >
      {/* Card header */}
      <div className="p-3 pb-0 flex items-start justify-between gap-2">
        <div className="flex gap-2 flex-wrap">
          {route.recommended && (
            <span className="bg-brand-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
              Recommended
            </span>
          )}
          <TrafficBadge level={route.traffic} />
        </div>
        <button
          id="route-details-btn"
          className="flex-none text-xs font-semibold text-brand-700 hover:text-brand-800 flex items-center gap-0.5 transition-colors"
        >
          Details <ArrowRight size={12} />
        </button>
      </div>

      {/* Duration + meta */}
      <div className="px-3 pt-2 pb-1">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-gray-900 tracking-tight">
            {route.durationMin} min
          </span>
          <span className="text-sm text-gray-500 font-medium">{route.distanceKm} km</span>
        </div>
        <p className="text-xs text-gray-700 font-semibold mt-0.5">
          Leave {departureTime} · arrive{' '}
          <span className="font-bold text-gray-900">{arrival}</span>
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          {route.label.split('·')[1]?.trim() ?? route.label}
        </p>
      </div>

      {/* First turn instruction */}
      {firstTurn && (
        <div className="px-3 py-2 border-t border-gray-50">
          <div className="flex items-start gap-2">
            <ArrowRight size={14} className="flex-none mt-0.5 text-brand-600" />
            <div>
              <p className="text-xs font-semibold text-gray-800">{firstTurn.text}</p>
              <p className="text-[11px] text-gray-400 mt-0.5">{firstTurn.detail}</p>
            </div>
          </div>
        </div>
      )}

      {/* Start navigation CTA */}
      <div className="p-3 pt-2">
        <button
          id="start-navigation-btn"
          onClick={startNav}
          className={[
            'w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold transition-all',
            isNavigating
              ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
              : 'bg-brand-700 hover:bg-brand-800 active:scale-[0.98] text-white shadow-sm',
          ].join(' ')}
          disabled={isNavigating}
        >
          <Navigation size={16} />
          {isNavigating ? 'Navigating…' : 'Start Live Navigation'}
        </button>
      </div>
    </div>
  );
}
