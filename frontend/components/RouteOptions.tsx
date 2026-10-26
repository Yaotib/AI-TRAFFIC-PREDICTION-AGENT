// ── RouteOptions — "All Route Options" section ─────────────────────────────
import { useRouteStore } from '../lib/store';
import { TrafficBadge } from './TrafficBadge';
import type { RouteOption } from '../lib/types';

const DOT_COLOR: Record<RouteOption['id'], string> = {
  A: 'bg-emerald-500',
  B: 'bg-red-500',
  C: 'bg-indigo-500',
};

export function RouteOptions() {
  const routeOptions = useRouteStore((s) => s.routeOptions);
  const selectedId   = useRouteStore((s) => s.selectedRouteId);
  const setSelected  = useRouteStore((s) => s.setSelectedRoute);

  return (
    <div className="px-3 mb-3">
      <h2 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2 px-0.5">
        All Route Options
      </h2>
      <div className="grid grid-cols-3 gap-2">
        {routeOptions.map((route) => {
          const isSelected = route.id === selectedId;
          return (
            <button
              key={route.id}
              id={`route-option-${route.id}`}
              onClick={() => setSelected(route.id)}
              className={[
                'text-left rounded-xl border p-3 transition-all',
                isSelected
                  ? 'border-brand-600 bg-brand-50 shadow-sm ring-1 ring-brand-300'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm',
              ].join(' ')}
            >
              {/* Route ID */}
              <div className="flex items-center gap-1.5 mb-2">
                <div className={`w-2 h-2 rounded-full flex-none ${DOT_COLOR[route.id]}`} />
                <span className="text-xs font-bold text-gray-800">Route {route.id}</span>
              </div>

              {/* Duration */}
              <div className="text-xl font-extrabold text-gray-900 leading-none">
                {route.durationMin} min
              </div>

              {/* Traffic level */}
              <div className="text-[10px] text-gray-500 mt-1 capitalize">{route.traffic} traffic</div>

              {/* Recommended badge OR delta */}
              <div className="mt-2">
                {route.recommended ? (
                  <span className="text-[10px] font-bold text-brand-700 bg-brand-100 px-1.5 py-0.5 rounded-full">
                    Recommended
                  </span>
                ) : route.deltaMin != null ? (
                  <span className="text-[10px] text-gray-400 font-medium">
                    +{route.deltaMin} min slower
                  </span>
                ) : null}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
