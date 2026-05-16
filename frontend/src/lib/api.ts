const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────

export interface IntakeData {
  first_name: string;
  last_name: string;
  dob: string;
  phone: string;
  email: string;
  sms_opt_in: boolean;
}

export interface IntakeResponse {
  patient_id: string;
  session_id: string;
}

export type StreamEvent =
  | { type: "text_delta"; text: string }
  | { type: "end"; session_id: string };

export interface ProviderSlot {
  id: string;
  slot_time: string;
  is_booked: boolean;
}

export interface Provider {
  id: string;
  name: string;
  specialty: string;
  body_parts: string[];
  bio: string | null;
  availability: ProviderSlot[];
}

// ── Helpers ────────────────────────────────────────────────────────

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${body ? ": " + body : ""}`);
  }
  return res.json() as Promise<T>;
}

// ── API surface ────────────────────────────────────────────────────

export interface SessionState {
  id: string;
  patient_id: string | null;
  conversation_state: unknown[];
  appointment_state: Record<string, unknown>;
  updated_at: string;
}

export function getSession(sessionId: string): Promise<SessionState> {
  return req<SessionState>(`/sessions/${sessionId}`);
}

export async function intakeSubmit(data: IntakeData): Promise<IntakeResponse> {
  const res = await req<IntakeResponse>("/intake", {
    method: "POST",
    body: JSON.stringify(data),
  });
  console.log("intakeSubmit response:", JSON.stringify(res));
  return res;
}

export async function* sendMessage(
  session_id: string,
  patient_id: string | null,
  message: string
): AsyncGenerator<StreamEvent, void, unknown> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, patient_id, message }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Chat failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const json = trimmed.slice(5).trim();
      if (!json) continue;
      try {
        yield JSON.parse(json) as StreamEvent;
      } catch {
        // malformed chunk — skip
      }
    }
  }
}

export function adminGetProviders(secret: string): Promise<{ providers: Provider[] }> {
  return req<{ providers: Provider[] }>("/admin/providers", {
    headers: { "X-Admin-Secret": secret },
  });
}

export async function adminToggleSlot(
  provider_id: string,
  slot_id: string,
  is_booked: boolean,
  secret: string
): Promise<void> {
  await req(`/admin/providers/${provider_id}/availability/${slot_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-Admin-Secret": secret },
    body: JSON.stringify({ is_booked }),
  });
}
