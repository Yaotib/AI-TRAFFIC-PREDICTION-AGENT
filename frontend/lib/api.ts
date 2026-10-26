
import type {
  AskResponse,
  ChatMessage,
  DecisionResult,
  PlanRequest,
} from "./types";

const BASE = (
  import.meta.env.VITE_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

async function post<T>(path: string, payload: unknown): Promise<T> {
  let res: Response;

  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(
      "Cannot reach the server. Check your connection and try again.",
    );
  }

  if (res.status === 429) {
    throw new Error(
      "Too many requests. Please wait a minute and try again.",
    );
  }

  if (!res.ok) {
    let detail = "The request failed.";

    try {
      const body = await res.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Keep the generic message.
    }

    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export function ask(messages: ChatMessage[]): Promise<AskResponse> {
  return post<AskResponse>("/api/agent/ask", { messages });
}

export function plan(body: PlanRequest): Promise<DecisionResult> {
  return post<DecisionResult>("/api/plan", body);
}
