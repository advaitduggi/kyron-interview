import { useState, useEffect, useCallback, useRef } from "react";
import { adminGetProviders, adminToggleSlot, type Provider, type ProviderSlot } from "../lib/api";

// ── Helpers ────────────────────────────────────────────────────────────────

const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

function formatDateHeader(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", timeZone: TZ,
  });
}

function formatSlotTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric", minute: "2-digit", hour12: true, timeZone: TZ,
  });
}

function formatTodayFull() {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
}

function initials(name: string) {
  return name.split(" ").filter((w) => /^[A-Z]/i.test(w)).slice(0, 2)
    .map((w) => w[0].toUpperCase()).join("");
}

function dateKey(iso: string) {
  // YYYY-MM-DD in local time for grouping
  const d = new Date(iso);
  return [
    d.toLocaleDateString("en-CA", { timeZone: TZ }), // gives YYYY-MM-DD
  ][0];
}

function slotsByDate(provider: Provider, days: number) {
  const now = Date.now();
  const cutoff = now + days * 24 * 60 * 60 * 1000;
  const future = provider.availability.filter((s) => {
    const t = new Date(s.slot_time).getTime();
    return t > now && t <= cutoff;
  });
  future.sort((a, b) => new Date(a.slot_time).getTime() - new Date(b.slot_time).getTime());

  const grouped = new Map<string, ProviderSlot[]>();
  for (const slot of future) {
    const key = dateKey(slot.slot_time);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(slot);
  }
  return grouped; // Map<dateKey, slots[]> ordered by date
}

function countAvailableThisWeek(provider: Provider) {
  const now = Date.now();
  const weekEnd = now + 7 * 24 * 60 * 60 * 1000;
  return provider.availability.filter((s) => {
    const t = new Date(s.slot_time).getTime();
    return t > now && t <= weekEnd && !s.is_booked;
  }).length;
}

// ── Sub-components ─────────────────────────────────────────────────────────

interface DateGroupProps {
  dateLabel: string;
  slots: ProviderSlot[];
  defaultOpen: boolean;
  onToggle: (slotId: string, isBooked: boolean) => void;
}

function DateGroup({ dateLabel, slots, defaultOpen, onToggle }: DateGroupProps) {
  const [open, setOpen] = useState(defaultOpen);
  const available = slots.filter((s) => !s.is_booked).length;

  return (
    <div className="date-group">
      <button
        className="date-group-header"
        onClick={() => setOpen((v) => !v)}
        type="button"
        aria-expanded={open}
      >
        <span className="date-group-label">{dateLabel}</span>
        <span className="date-group-meta">
          {available}/{slots.length} open
          <span className={`date-group-chevron${open ? " open" : ""}`}>›</span>
        </span>
      </button>

      {open && (
        <ul className="slot-list">
          {slots.map((s) => (
            <li
              key={s.id}
              className={`slot-item${s.is_booked ? " slot-item--booked" : ""}`}
              onClick={() => onToggle(s.id, s.is_booked)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onToggle(s.id, s.is_booked);
                }
              }}
              aria-label={`${formatSlotTime(s.slot_time)} — ${s.is_booked ? "Booked" : "Available"}`}
            >
              <span className="slot-item-left">
                <span className={`slot-dot ${s.is_booked ? "slot-dot-booked" : "slot-dot-open"}`} />
                <span className="slot-item-body">
                  <span className="slot-item-time">{formatSlotTime(s.slot_time)}</span>
                  {s.is_booked && s.patient_name && (
                    <span className="slot-patient-info">
                      <span className="slot-patient-name">{s.patient_name}</span>
                      {s.reason && <span className="slot-patient-reason"> • {s.reason}</span>}
                      <span className="slot-patient-meta">
                        {s.patient_phone && (
                          <span className="slot-patient-phone">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.7 12.5 19.79 19.79 0 0 1 1.64 3.89 2 2 0 0 1 3.61 2H6.5a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L7.5 9.59a16 16 0 0 0 6 6l.75-.75a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>
                            </svg>
                            {s.patient_phone}
                          </span>
                        )}
                        {s.appointment_id && (
                          <span className="slot-confirmation">{s.appointment_id}</span>
                        )}
                      </span>
                    </span>
                  )}
                </span>
              </span>
              <span className="slot-action">
                {s.is_booked ? "Unblock" : "Block"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

const RANGE_OPTIONS = [7, 14, 30] as const;
type DayRange = (typeof RANGE_OPTIONS)[number];

export default function AdminDashboard() {
  const [secret, setSecret]       = useState("");
  const [authed, setAuthed]       = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading]     = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [toast, setToast]         = useState<string | null>(null);
  const [dayRange, setDayRange]   = useState<DayRange>(7);
  const secretRef = useRef(secret);
  useEffect(() => { secretRef.current = secret; }, [secret]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2000);
    return () => clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    if (!authed) return;
    const interval = setInterval(fetchProviders, 30000);
    return () => clearInterval(interval);
  }, [authed]); // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchProviders() {
    setLoading(true);
    try {
      const data = await adminGetProviders(secretRef.current);
      setProviders(data.providers);
    } catch {
      setToast("Refresh failed");
    } finally {
      setLoading(false);
    }
  }

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
      setProviders((prev) =>
        prev.map((p) =>
          p.id !== provider.id ? p : {
            ...p,
            availability: p.availability.map((s) =>
              s.id === slotId ? { ...s, is_booked: newBooked } : s
            ),
          }
        )
      );
      try {
        await adminToggleSlot(provider.id, slotId, newBooked, secretRef.current);
        setToast(newBooked ? "Slot blocked" : "Slot opened");
      } catch {
        setProviders((prev) =>
          prev.map((p) =>
            p.id !== provider.id ? p : {
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
              <button className="admin-auth-btn" type="submit" disabled={loading || !secret}>
                {loading ? "Verifying…" : "Sign in"}
              </button>
              {authError && <p className="admin-auth-error">{authError}</p>}
            </form>
          </div>
        </div>
      ) : (
        <div className="admin-content">
          <div className="admin-content-top">
            <div>
              <h2 className="admin-content-heading">Provider availability</h2>
              <p className="admin-today">{formatTodayFull()}</p>
            </div>
            <div className="admin-toolbar">
              <div className="range-toggle">
                {RANGE_OPTIONS.map((d) => (
                  <button
                    key={d}
                    className={`range-btn${dayRange === d ? " range-btn--active" : ""}`}
                    onClick={() => setDayRange(d)}
                    type="button"
                  >
                    {d}d
                  </button>
                ))}
              </div>
              <button
                className="refresh-btn"
                onClick={() => void fetchProviders()}
                disabled={loading}
                type="button"
              >
                {loading ? "…" : "↻ Refresh"}
              </button>
            </div>
          </div>

          <div className="provider-grid">
            {providers.map((p) => {
              const grouped = slotsByDate(p, dayRange);
              const weekAvail = countAvailableThisWeek(p);
              const dateKeys = Array.from(grouped.keys());

              return (
                <div key={p.id} className="provider-card">
                  <div className="provider-card-head">
                    <div className="provider-avatar">{initials(p.name)}</div>
                    <div className="provider-card-info">
                      <div className="provider-card-name">{p.name}</div>
                      <span className="specialty-badge">{p.specialty}</span>
                    </div>
                  </div>

                  <p className="provider-week-summary">
                    {weekAvail} available slot{weekAvail !== 1 ? "s" : ""} this week
                  </p>

                  {dateKeys.length === 0 ? (
                    <p className="no-slots-msg">No upcoming slots in next {dayRange} days</p>
                  ) : (
                    <div className="date-groups">
                      {dateKeys.map((key, i) => {
                        const slots = grouped.get(key)!;
                        return (
                          <DateGroup
                            key={key}
                            dateLabel={formatDateHeader(slots[0].slot_time)}
                            slots={slots}
                            defaultOpen={i === 0}
                            onToggle={(slotId, isBooked) =>
                              void toggleSlot(p, slotId, isBooked)
                            }
                          />
                        );
                      })}
                    </div>
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
