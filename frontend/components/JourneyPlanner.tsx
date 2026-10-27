
import { useState } from "react";
import { AlertCircle, Clock3, Route, Sparkles } from "lucide-react";
import { plan } from "../lib/api";
import { useRouteStore } from "../lib/store";
import type { DecisionResult, PlanRequest } from "../lib/types";

function defaultLocalDateTime(): string {
  const date = new Date();
  date.setMinutes(date.getMinutes() + 60);
  date.setSeconds(0, 0);

  const pad = (value: number) => String(value).padStart(2, "0");

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate(),
  )}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatClock(value: string | null | undefined): string {
  if (!value) return "Not available";

  const timePart = value.includes("T")
    ? value.split("T")[1].slice(0, 5)
    : value.slice(0, 5);

  const [hoursText, minutes] = timePart.split(":");
  const hours = Number(hoursText);

  if (!Number.isFinite(hours) || !minutes) return value;

  return `${hours % 12 || 12}:${minutes} ${hours >= 12 ? "PM" : "AM"}`;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Not available";

  const [datePart, timePart] = value.split("T");
  if (!timePart) return value;

  return `${datePart} at ${formatClock(value)}`;
}

function statusLabel(result: DecisionResult): string {
  switch (result.status) {
    case "recommended":
      return "Recommendation ready";
    case "keep_desired_time":
      return "Your preferred time looks suitable";
    case "no_feasible_time":
      return "No feasible time found";
    case "insufficient_data":
      return "Not enough data for a recommendation";
  }
}

export function JourneyPlanner() {
  const origin = useRouteStore((state) => state.origin);
  const destination = useRouteStore((state) => state.destination);
  const setPlanningResult = useRouteStore(
    (state) => state.setPlanningResult,
);

  const [mode, setMode] = useState<PlanRequest["mode"]>("arrive_by");
  const [timeLocal, setTimeLocal] = useState(defaultLocalDateTime);
  const [result, setResult] = useState<DecisionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handlePlan() {
    if (!origin.trim() || !destination.trim()) {
      setError("Enter both an origin and a destination.");
      return;
    }

    if (origin.trim().toLowerCase() === destination.trim().toLowerCase()) {
      setError("Origin and destination must be different.");
      return;
    }

    if (!timeLocal) {
      setError("Choose a date and time first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setPlanningResult(null);

    try {
      const response = await plan({
        origin: origin.trim(),
        destination: destination.trim(),
        mode,
        time_local: timeLocal,
      });

      setResult(response);
      setPlanningResult(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not plan this journey. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  const recommended = result?.recommended;

  return (
    <section className="px-3 pb-4 space-y-3">
      <div className="rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <div className="rounded-lg bg-brand-50 p-2 text-brand-700">
            <Sparkles size={17} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-gray-900">
              AI Journey Planner
            </h2>
            <p className="text-xs text-gray-500">
              Plan around your schedule
            </p>
          </div>
        </div>

        <fieldset className="mb-3">
          <legend className="mb-2 text-xs font-semibold text-gray-700">
            What matters most?
          </legend>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => {
                setMode("arrive_by");
                setResult(null);
                setError("");
              }}
              aria-pressed={mode === "arrive_by"}
              className={`rounded-lg border px-2 py-2 text-xs font-semibold transition-colors ${
                mode === "arrive_by"
                  ? "border-brand-600 bg-brand-50 text-brand-800"
                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              Arrive by
            </button>

            <button
              type="button"
              onClick={() => {
                setMode("depart_around");
                setResult(null);
                setError("");
              }}
              aria-pressed={mode === "depart_around"}
              className={`rounded-lg border px-2 py-2 text-xs font-semibold transition-colors ${
                mode === "depart_around"
                  ? "border-brand-600 bg-brand-50 text-brand-800"
                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              Depart around
            </button>
          </div>
        </fieldset>

        <label
          htmlFor="planning-time"
          className="mb-1 block text-xs font-semibold text-gray-700"
        >
          {mode === "arrive_by" ? "I need to arrive by" : "I want to leave around"}
        </label>

        <input
          id="planning-time"
          type="datetime-local"
          value={timeLocal}
          onChange={(event) => {
            setTimeLocal(event.target.value);
            setResult(null);
            setError("");
          }}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-brand-600 focus:ring-1 focus:ring-brand-300"
        />

        <button
          type="button"
          onClick={handlePlan}
          disabled={loading}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-700 px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Route size={16} />
          {loading ? "Planning your journey..." : "Plan Journey"}
        </button>

        {error && (
          <div
            role="alert"
            className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700"
          >
            <AlertCircle size={15} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {result && (
        <div
          aria-live="polite"
          className="space-y-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm"
        >
          <div>
            <p className="text-xs font-semibold text-brand-700">
              {statusLabel(result)}
            </p>
            <h3 className="mt-1 text-sm font-bold text-gray-900">
              {result.origin_name} → {result.destination_name}
            </h3>
            <p className="mt-1 text-xs text-gray-500">
              {result.mode === "arrive_by"
                ? `Arrival deadline: ${formatDateTime(result.deadline_local)}`
                : `Preferred departure: ${formatDateTime(result.desired_departure_local)}`}
            </p>
          </div>

          {recommended ? (
            <div className="rounded-xl border border-brand-200 bg-brand-50 p-3">
              <div className="mb-2 flex items-center gap-2 text-xs font-bold text-brand-800">
                <Clock3 size={15} />
                Recommended journey
              </div>

              <p className="text-2xl font-extrabold text-gray-900">
                {recommended.duration_min} min
              </p>

              <div className="mt-2 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[11px] text-gray-500">Leave</p>
                  <p className="text-sm font-bold text-gray-900">
                    {formatClock(recommended.departure_local)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-500">Arrive</p>
                  <p className="text-sm font-bold text-gray-900">
                    {formatClock(recommended.arrival_local)}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-500">Distance</p>
                  <p className="text-sm font-bold text-gray-900">
                    {recommended.distance_km.toFixed(1)} km
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-500">Traffic delay estimate</p>
                  <p className="text-sm font-bold text-gray-900">
                    {recommended.traffic_delay_min == null
                      ? "Unavailable"
                      : `${recommended.traffic_delay_min} min`}
                  </p>
                </div>
              </div>

              {result.time_saved_min != null && (
                <p className="mt-3 text-xs text-gray-700">
                  Time difference from baseline:{" "}
                  <strong>{result.time_saved_min} min</strong>
                </p>
              )}

              {result.deadline_margin_min != null && (
                <p className="mt-1 text-xs text-gray-700">
                  Estimated deadline margin:{" "}
                  <strong>{result.deadline_margin_min} min</strong>
                </p>
              )}
            </div>
          ) : (
            <p className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
              The backend did not produce a recommended journey for this request.
              Check the explanation and warnings below.
            </p>
          )}

          {result.candidates.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-500">
                Candidate departure times
              </h4>

              <div className="space-y-2">
                {result.candidates.map((candidate, index) => {
                  const isRecommended =
                    recommended != null &&
                    candidate.departure_local === recommended.departure_local;

                  return (
                    <div
                      key={`${candidate.departure_local}-${index}`}
                      className={`flex items-center justify-between gap-3 rounded-lg border p-2 ${
                        isRecommended
                          ? "border-brand-300 bg-brand-50"
                          : "border-gray-100 bg-gray-50"
                      }`}
                    >
                      <div>
                        <p className="text-xs font-semibold text-gray-800">
                          Leave {formatClock(candidate.departure_local)}
                          {isRecommended ? " · Recommended" : ""}
                        </p>
                        <p className="text-[11px] text-gray-500">
                          Arrive {formatClock(candidate.arrival_local)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-gray-900">
                          {candidate.duration_min} min
                        </p>
                        <p className="text-[11px] text-gray-500">
                          {candidate.distance_km.toFixed(1)} km
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="rounded-lg border border-gray-200 p-3">
            <p className="text-xs font-bold text-gray-800">
              Data and estimate details
            </p>
            <p className="mt-1 text-xs text-gray-600">
              Source: {result.labels.source}
            </p>
            <p className="mt-1 text-xs text-gray-600">
              Estimate type: {result.labels.duration_type}
            </p>
            <p className="mt-1 text-xs text-gray-600">
              {result.labels.note}
            </p>
            {result.context?.note && (
              <p className="mt-2 text-xs text-gray-500">
                {result.context.note}
              </p>
            )}
          </div>

          {result.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="mb-2 flex items-center gap-2 text-xs font-bold text-amber-900">
                <AlertCircle size={15} />
                Important notes
              </p>
              <ul className="list-disc space-y-1 pl-4 text-xs text-amber-900">
                {result.warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
