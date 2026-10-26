// ── App — root layout ──────────────────────────────────────────────────────
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useRouteStore } from '../lib/store';
import { fetchRoutes } from '../lib/mock-data';
import { useTrafficSSE } from '../lib/useTrafficSSE';

import { TopBar }        from '../components/TopBar';
import { LocationPanel } from '../components/LocationPanel';
import { FilterBar }     from '../components/FilterBar';
import { RouteCard }     from '../components/RouteCard';
import { RouteOptions }  from '../components/RouteOptions';
import { AlertBanner }   from '../components/AlertBanner';
import { SidebarFooter } from '../components/SidebarFooter';
import { LiveStatusBar } from '../components/LiveStatusBar';
import { MapPanel }      from './MapPanel';

export default function App() {
  const origin      = useRouteStore((s) => s.origin);
  const destination = useRouteStore((s) => s.destination);
  const departure   = useRouteStore((s) => s.departureTime);
  const applyUpdate = useRouteStore((s) => s.applySSEUpdate);
  const setUpdated  = useRouteStore((s) => s.setLastUpdated);

  // ── TanStack Query v5: load routes on params change ───────────────────
  const { isLoading, data } = useQuery({
    queryKey: ['routes', origin, destination, departure],
    queryFn: () => fetchRoutes({ origin, destination, departureTime: departure }),
    staleTime: 30_000,
  });

  // Sync query data → Zustand store (v5 pattern — no onSuccess option)
  useEffect(() => {
    if (data) {
      applyUpdate({ type: 'route_update', routes: data.routes });
    }
  }, [data, applyUpdate]);

  // ── SSE: subscribe to live traffic stream ─────────────────────────────
  useTrafficSSE();

  // ── Tick "last updated" display every 10s ─────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      setUpdated(new Date());
    }, 10_000);
    return () => clearInterval(interval);
  }, [setUpdated]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50 font-sans">
      {/* ── Top bar (full width) ── */}
      <TopBar />

      {/* ── Body: sidebar + map ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside
          id="route-sidebar"
          className="w-[360px] shrink-0 flex flex-col overflow-y-auto bg-white border-r border-gray-100 shadow-sm"
        >
          <LocationPanel />
          <div className="h-px bg-gray-100 mx-4" />
          <div className="pt-3">
            <FilterBar />
          </div>
          <div className="h-px bg-gray-100 mx-4 mb-3" />

          {isLoading ? (
            <div className="px-3 space-y-3">
              <div className="skeleton h-40 w-full" />
              <div className="skeleton h-24 w-full" />
              <div className="skeleton h-16 w-full" />
            </div>
          ) : (
            <>
              <RouteCard />
              <RouteOptions />
              <AlertBanner />
            </>
          )}

          <SidebarFooter />
        </aside>

        {/* Map */}
        <main id="map-container" className="flex-1 relative overflow-hidden">
          <MapPanel />
          <LiveStatusBar />
        </main>
      </div>
    </div>
  );
}
