// ── Types for MetroRoute UI ─────────────────────────────────────────────────

export type TrafficLevel = 'light' | 'moderate' | 'heavy';

export interface RouteOption {
  id: 'A' | 'B' | 'C';
  label: string;
  durationMin: number;
  distanceKm: number;
  traffic: TrafficLevel;
  deltaMin: number | null; // null = fastest (reference)
  recommended: boolean;
  color: string;            // hex, used for map polyline
  coordinates: [number, number][]; // GeoJSON LineString coords
}

export interface TurnInstruction {
  id: string;
  text: string;
  detail: string;
  distanceM: number;
}

export interface TrafficAlert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  routeId: RouteOption['id'];
  title: string;
  body: string;
}

export interface RouteState {
  origin: string;
  destination: string;
  departureTime: string;       // ISO string or "now"
  estimatedArrival: string;    // display string, e.g. "7:42 AM"
  selectedRouteId: RouteOption['id'];
  routeOptions: RouteOption[];
  turnInstructions: TurnInstruction[];
  alerts: TrafficAlert[];
  activeFilter: 'fastest' | 'no-tolls' | 'scenic';
  isNavigating: boolean;
  liveGpsLocked: boolean;
  lastUpdated: Date | null;
}

export interface RouteActions {
  setOrigin: (v: string) => void;
  setDestination: (v: string) => void;
  setDepartureTime: (v: string) => void;
  setSelectedRoute: (id: RouteOption['id']) => void;
  setActiveFilter: (f: RouteState['activeFilter']) => void;
  startNavigation: () => void;
  stopNavigation: () => void;
  applySSEUpdate: (payload: SSERouteUpdate) => void;
  setLiveGps: (locked: boolean) => void;
  setLastUpdated: (d: Date) => void;
}

export interface SSERouteUpdate {
  type: 'route_update' | 'alert' | 'gps_status';
  routes?: Pick<RouteOption, 'id' | 'durationMin' | 'traffic' | 'deltaMin'>[];
  alert?: TrafficAlert;
  gpsLocked?: boolean;
}
