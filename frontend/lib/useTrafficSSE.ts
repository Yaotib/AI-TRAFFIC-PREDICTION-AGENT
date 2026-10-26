// ── Native SSE hook for live traffic updates ───────────────────────────────
import { useEffect, useRef } from 'react';
import { useRouteStore } from '../lib/store';
import type { SSERouteUpdate } from '../lib/types';

const SSE_URL = import.meta.env.VITE_TRAFFIC_SSE_URL as string | undefined;

/**
 * Connects to the backend SSE endpoint when a URL is configured.
 * Falls back to a mock simulation when no URL is set (demo mode).
 */
export function useTrafficSSE() {
  const applySSEUpdate = useRouteStore((s) => s.applySSEUpdate);
  const setLastUpdated = useRouteStore((s) => s.setLastUpdated);
  const setLiveGps    = useRouteStore((s) => s.setLiveGps);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const esRef    = useRef<EventSource | null>(null);

  useEffect(() => {
    if (SSE_URL) {
      // Real SSE connection
      const es = new EventSource(SSE_URL);
      esRef.current = es;

      es.addEventListener('route_update', (e) => {
        try {
          const data = JSON.parse((e as MessageEvent).data) as SSERouteUpdate;
          applySSEUpdate(data);
        } catch { /* ignore parse errors */ }
      });

      es.addEventListener('alert', (e) => {
        try {
          const data = JSON.parse((e as MessageEvent).data) as SSERouteUpdate;
          applySSEUpdate(data);
        } catch { /* ignore parse errors */ }
      });

      es.onerror = () => {
        setLiveGps(false);
      };

      return () => { es.close(); };
    } else {
      // Demo simulation: update "last updated" timestamp every 10s
      setLiveGps(true);
      timerRef.current = setInterval(() => {
        setLastUpdated(new Date());
        // Occasionally simulate a small route duration change
        if (Math.random() < 0.3) {
          applySSEUpdate({
            type: 'route_update',
            routes: [
              { id: 'B', durationMin: 33 + Math.round((Math.random() - 0.5) * 4), traffic: 'heavy', deltaMin: 6 },
              { id: 'C', durationMin: 36 + Math.round((Math.random() - 0.5) * 2), traffic: 'moderate', deltaMin: 9 },
            ],
          });
        }
      }, 10_000);

      return () => {
        if (timerRef.current) clearInterval(timerRef.current);
      };
    }
  }, [applySSEUpdate, setLastUpdated, setLiveGps]);
}
