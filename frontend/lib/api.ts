// ── Mock/demo data for MetroRoute ──────────────────────────────────────────
import type { RouteOption, TurnInstruction, TrafficAlert } from './types';

// Simulated Accra coordinates: Madina ↔ Harbour/Central
const ORIGIN_LNG_LAT: [number, number] = [-0.1692, 5.6480];  // Madina area
const DEST_LNG_LAT:   [number, number] = [-0.2070, 5.5502];  // Harbour/Central

// Simple arc generator for demo polylines
function arcCoords(
  from: [number, number],
  to: [number, number],
  curvature = 0,
  steps = 30,
): [number, number][] {
  return Array.from({ length: steps + 1 }, (_, i) => {
    const t = i / steps;
    const lng = from[0] + (to[0] - from[0]) * t;
    const lat = from[1] + (to[1] - from[1]) * t + Math.sin(Math.PI * t) * curvature;
    return [lng, lat];
  });
}

export const MOCK_ROUTES: RouteOption[] = [
  {
    id: 'A',
    label: 'Route A · Ridge Expressway',
    durationMin: 27,
    distanceKm: 14.2,
    traffic: 'light',
    deltaMin: null,
    recommended: true,
    color: '#059669',
    coordinates: arcCoords(ORIGIN_LNG_LAT, DEST_LNG_LAT, 0.025),
  },
  {
    id: 'B',
    label: 'Route B · Bay Bypass',
    durationMin: 33,
    distanceKm: 15.8,
    traffic: 'heavy',
    deltaMin: 6,
    recommended: false,
    color: '#ef4444',
    coordinates: arcCoords(ORIGIN_LNG_LAT, DEST_LNG_LAT, -0.02),
  },
  {
    id: 'C',
    label: 'Route C · North Bay Channel',
    durationMin: 36,
    distanceKm: 17.1,
    traffic: 'moderate',
    deltaMin: 9,
    recommended: false,
    color: '#6366f1',
    coordinates: arcCoords(ORIGIN_LNG_LAT, DEST_LNG_LAT, 0.005),
  },
];

export const MOCK_TURNS: TurnInstruction[] = [
  {
    id: 't1',
    text: 'Merge onto Ridge Pkwy toward Harbour Dist.',
    detail: 'In 650m take Exit 14B · No delays reported',
    distanceM: 650,
  },
  {
    id: 't2',
    text: 'Keep right at the fork onto Independence Ave',
    detail: 'Continue 2.1 km · Light traffic',
    distanceM: 2100,
  },
  {
    id: 't3',
    text: 'Turn left onto Harbour Rd',
    detail: 'In 400m · Destination on right',
    distanceM: 400,
  },
];

export const MOCK_ALERTS: TrafficAlert[] = [
  {
    id: 'alert-1',
    severity: 'warning',
    routeId: 'B',
    title: 'Traffic Alert on Route B',
    body: 'Road maintenance on Bay Bypass adds ~6 minutes. Route A remains optimal.',
  },
];

// Simulate an API call that resolves after a short delay
export async function fetchRoutes(_params: {
  origin: string;
  destination: string;
  departureTime: string;
}): Promise<{ routes: RouteOption[]; turns: TurnInstruction[]; alerts: TrafficAlert[] }> {
  await new Promise(r => setTimeout(r, 800));
  return { routes: MOCK_ROUTES, turns: MOCK_TURNS, alerts: MOCK_ALERTS };
}
