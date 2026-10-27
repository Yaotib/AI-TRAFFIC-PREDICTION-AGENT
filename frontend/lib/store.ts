// ── Zustand store for MetroRoute ───────────────────────────────────────────
import { create } from 'zustand';
import { MOCK_ROUTES, MOCK_TURNS, MOCK_ALERTS } from '../lib/mock-data';
import type {
  RouteState,
  RouteActions,
  SSERouteUpdate,
  DecisionResult,
} from '../lib/types';

type Store = RouteState &
  RouteActions & {
    planningResult: DecisionResult | null;
    setPlanningResult: (result: DecisionResult | null) => void;
  };

export const useRouteStore = create<Store>((set) => ({
  // ── Initial state ──────────────────────────────────────────────────────
  origin: 'Your current location',
  destination: 'Harbour Station',
  departureTime: '7:15 AM',
  estimatedArrival: '7:42 AM',
  selectedRouteId: 'A',
  routeOptions: MOCK_ROUTES,
  turnInstructions: MOCK_TURNS,
  alerts: MOCK_ALERTS,
  activeFilter: 'fastest',
  isNavigating: false,
  liveGpsLocked: false,
  lastUpdated: null,
  planningResult: null,

  // ── Actions ────────────────────────────────────────────────────────────
  setOrigin: (v) => set({ origin: v }),
  setDestination: (v) => set({ destination: v }),
  setDepartureTime: (v) => set({ departureTime: v }),

  setSelectedRoute: (id) => set({ selectedRouteId: id }),
  setPlanningResult: (result) => set({ planningResult: result }),
  setActiveFilter: (f) => set({ activeFilter: f }),

  startNavigation: () => set({ isNavigating: true }),
  stopNavigation: () => set({ isNavigating: false }),

  setLiveGps: (locked) => set({ liveGpsLocked: locked }),
  setLastUpdated: (d) => set({ lastUpdated: d }),

  applySSEUpdate: (payload: SSERouteUpdate) => {
    if (payload.type === 'route_update' && payload.routes) {
      set((state) => ({
        routeOptions: state.routeOptions.map((r) => {
          const update = payload.routes!.find((u) => u.id === r.id);
          return update ? { ...r, ...update } : r;
        }),
        lastUpdated: new Date(),
      }));
    } else if (payload.type === 'alert' && payload.alert) {
      set((state) => ({
        alerts: [...state.alerts.filter((a) => a.id !== payload.alert!.id), payload.alert!],
      }));
    } else if (payload.type === 'gps_status') {
      set({ liveGpsLocked: payload.gpsLocked ?? false });
    }
  },
}));
