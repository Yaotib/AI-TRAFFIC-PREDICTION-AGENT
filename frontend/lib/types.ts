
 // ── MetroRoute UI Types ─────────────────────────────────────────────

export type TrafficLevel = "light" | "moderate" | "heavy";

export interface RouteOption {
  id: "A" | "B" | "C";
  label: string;
  durationMin: number;
  distanceKm: number;
  traffic: TrafficLevel;
  deltaMin: number | null;
  recommended: boolean;
  color: string;
  coordinates: [number, number][];
}

export interface TurnInstruction {
  id: string;
  text: string;
  detail: string;
  distanceM: number;
}

export interface TrafficAlert {
  id: string;
  severity: "info" | "warning" | "critical";
  routeId: RouteOption["id"];
  title: string;
  body: string;
}

export interface RouteState {
  origin: string;
  destination: string;
  departureTime: string;
  estimatedArrival: string;
  selectedRouteId: RouteOption["id"];
  routeOptions: RouteOption[];
  turnInstructions: TurnInstruction[];
  alerts: TrafficAlert[];
  activeFilter: "fastest" | "no-tolls" | "scenic";
  isNavigating: boolean;
  liveGpsLocked: boolean;
  lastUpdated: Date | null;
}

export interface RouteActions {
  setOrigin: (v: string) => void;
  setDestination: (v: string) => void;
  setDepartureTime: (v: string) => void;
  setSelectedRoute: (id: RouteOption["id"]) => void;
  setActiveFilter: (f: RouteState["activeFilter"]) => void;
  startNavigation: () => void;
  stopNavigation: () => void;
  applySSEUpdate: (payload: SSERouteUpdate) => void;
  setLiveGps: (locked: boolean) => void;
  setLastUpdated: (d: Date) => void;
}

export interface SSERouteUpdate {
  type: "route_update" | "alert" | "gps_status";
  routes?: Pick<
    RouteOption,
    "id" | "durationMin" | "traffic" | "deltaMin"
  >[];
  alert?: TrafficAlert;
  gpsLocked?: boolean;
}

// ── AI Traffic Prediction / Decision Engine Types ────────────────────

export type CandidateView = {
  departure_local: string;
  arrival_local: string;
  duration_min: number;
  static_duration_min: number | null;
  traffic_delay_min: number | null;
  distance_km: number;
  route_description: string | null;
  alternatives_count: number;
  coordinates: [number, number][] | null;
};

export type DataLabels = {
  source: string;
  duration_type: string;
  simulated: boolean;
  note: string;
};

export type ContextInfo = {
  weather: {
    available: boolean;
    source?: string;
    hour_local?: string;
    precipitation_mm?: number | null;
    precipitation_probability_pct?: number | null;
    reason?: string;
  };
  calendar: {
    available: boolean;
    source?: string;
    day_of_week?: string;
    is_weekend?: boolean;
    is_public_holiday?: boolean;
    holiday_name?: string | null;
    reason?: string;
  };
  note: string;
};

export type DecisionResult = {
  status:
    | "recommended"
    | "keep_desired_time"
    | "no_feasible_time"
    | "insufficient_data";
  mode: "arrive_by" | "depart_around";
  rule_applied: string;
  origin_name: string;
  destination_name: string;
  date_local: string;
  deadline_local: string | null;
  desired_departure_local: string | null;
  recommended: CandidateView | null;
  baseline: CandidateView | null;
  baseline_label: string | null;
  time_saved_min: number | null;
  deadline_margin_min: number | null;
  spread_min: number;
  buffer_min: number | null;
  gain_min: number;
  candidates: CandidateView[];
  warnings: string[];
  labels: DataLabels;
  context: ContextInfo | null;
};

export type ToolTrace = {
  tool: string;
  arguments: Record<string, unknown>;
  ok: boolean;
  summary: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AskResponse = {
  reply: string;
  explanation_source: "llm" | "template" | "none";
  notice: string | null;
  result: DecisionResult | null;
  trace: ToolTrace[];
};

export type PlanRequest = {
  origin: string;
  destination: string;
  mode: "arrive_by" | "depart_around";
  time_local: string;
};
