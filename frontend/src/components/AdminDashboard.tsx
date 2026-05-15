import { useState, useEffect, useCallback } from "react";
import { adminGetProviders, adminToggleSlot, type Provider } from "../lib/api";

function formatSlotTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function initials(name: string) {
  return name
    .split(" ")
    .filter((w) => /^[A-Z]/i.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

function nextSlots(provider: Provider, n = 5) {
  const now = Date.now();
  return provider.availability
    .filter((s) => new Date(s.slot_time).getTime() > now)
    .sort((a, b) => new Date(a.slot_time).getTime() - new Date(b.slot_time).getTime())
    .slice(0, n);
}

export default function AdminDashboard() {
  const [secret, setSecret]       = useState("");
  const [authed, setAuthed]       = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading]     = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [toast, setToast]         = useState<string | null>(null);
  const secretRef = useState(secret)[0]; // stable ref for callbacks

  // dismiss toast after 2 s
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2000);
    return () => clearTimeout(t);
  }, [toast]);

  async function handleAuth(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setAuthError(null);
    try {
      const data = await adminGetProviders(secret);
      setProviders(data.providers);
      setAuthed(true);
    } catch {
      setAuthError("Invalid secret or server error.");
    } finally {
      setLoading(false);
    }
  }

  const toggleSlot = useCallback(
    async (provider: Provider, slotId: string, currentBooked: boolean) => {
      const newBooked = !currentBooked;
      // Optimistic update
      setProviders((prev) =>
        prev.map((p) =>
          p.id !== provider.id
            ? p
            : {
                ...p,
                availability: p.availability.map((s) =>
                  s.id === slotId ? { ...s, is_booked: newBooked } : s
                ),
              }
        )
      );
      try {
        await adminToggleSlot(provider.id, slotId, newBooked, secretRef);
        setToast(newBooked ? "Slot blocked" : "Slot opened");
      } catch {
        // Revert on failure
        setProviders((prev) =>
          prev.map((p) =>
            p.id !== provider.id
              ? p
              : {
                  ...p,
                  availability: p.availability.map((s) =>
                    s.id === slotId ? { ...s, is_booked: currentBooked } : s
                  ),
                }
          )
        );
        setToast("Update failed — please retry");
      }
    },
    [secretRef]
  );

  return (
    <div className="admin-root">
      <header className="admin-header">
        <span className="admin-header-title">Kyron Admin</span>
      </header>

      {!authed ? (
        <div className="admin-auth">
          <div className="admin-auth-card">
            <h1 className="admin-auth-heading">Admin access</h1>
            <p className="admin-auth-sub">Enter your admin secret to continue.</p>
            <form onSubmit={handleAuth}>
              <input
                className="admin-auth-input"
                type="password"
                placeholder="Admin secret"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                autoFocus
              />
              <button
                className="admin-auth-btn"
                type="submit"
                disabled={loading || !secret}
              >
                {loading ? "Verifying…" : "Sign in"}
              </button>
              {authError && <p className="admin-auth-error">{authError}</p>}
            </form>
          </div>
        </div>
      ) : (
        <div className="admin-content">
          <h2 className="admin-content-heading">Provider availability</h2>
          <div className="provider-grid">
            {providers.map((p) => {
              const slots = nextSlots(p);
              return (
                <div key={p.id} className="provider-card">
                  <div className="provider-card-head">
                    <div className="provider-avatar">{initials(p.name)}</div>
                    <div className="provider-card-info">
                      <div className="provider-card-name">{p.name}</div>
                      <span className="specialty-badge">{p.specialty}</span>
                    </div>
                  </div>

                  {slots.length === 0 ? (
                    <p style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
                      No upcoming slots
                    </p>
                  ) : (
                    <ul className="slot-list">
                      {slots.map((s) => (
                        <li
                          key={s.id}
                          className="slot-item"
                          onClick={() => void toggleSlot(p, s.id, s.is_booked)}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              void toggleSlot(p, s.id, s.is_booked);
                            }
                          }}
                          aria-label={`${formatSlotTime(s.slot_time)} — ${s.is_booked ? "Blocked" : "Available"}`}
                        >
                          <span className="slot-item-left">
                            <span
                              className={`slot-dot ${
                                s.is_booked ? "slot-dot-booked" : "slot-dot-open"
                              }`}
                            />
                            {formatSlotTime(s.slot_time)}
                          </span>
                          <span className="slot-label">
                            {s.is_booked ? "Blocked" : "Available"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
