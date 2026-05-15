import { useState } from "react";
import { intakeSubmit } from "../lib/api";

interface Props {
  onComplete: (patientId: string, sessionId: string) => void;
}

export default function IntakeForm({ onComplete }: Props) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName]   = useState("");
  const [dob, setDob]             = useState("");
  const [phone, setPhone]         = useState("");
  const [email, setEmail]         = useState("");
  const [smsOptIn, setSmsOptIn]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!firstName || !lastName || !dob || !phone || !email) {
      setError("Please fill in all required fields.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await intakeSubmit({
        first_name: firstName,
        last_name: lastName,
        dob,
        phone,
        email,
        sms_opt_in: smsOptIn,
      });
      onComplete(res.patient_id, res.session_id);
    } catch {
      setError("Unable to connect. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="intake-root">
      {/* ── Brand panel ── */}
      <div className="intake-brand">
        <div className="intake-brand-logo">
          <div className="intake-brand-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="9" y="2" width="2" height="16" rx="1" fill="white" opacity="0.9"/>
              <rect x="2" y="9" width="16" height="2" rx="1" fill="white" opacity="0.9"/>
            </svg>
          </div>
          <span className="intake-brand-name">Kyron</span>
        </div>

        <p className="intake-brand-tagline">Your health, beautifully managed.</p>
        <p className="intake-brand-caption">
          Seamless appointment scheduling with the right specialist —
          guided by an intelligent assistant that understands your needs.
        </p>

        {/* decorative geometric — concentric circles */}
        <svg
          className="intake-brand-geo"
          width="420"
          height="420"
          viewBox="0 0 420 420"
          fill="none"
        >
          <circle cx="210" cy="210" r="200" stroke="white" strokeWidth="1"/>
          <circle cx="210" cy="210" r="150" stroke="white" strokeWidth="1"/>
          <circle cx="210" cy="210" r="100" stroke="white" strokeWidth="1"/>
          <circle cx="210" cy="210" r="50"  stroke="white" strokeWidth="1"/>
          <line x1="10"  y1="210" x2="410" y2="210" stroke="white" strokeWidth="0.75"/>
          <line x1="210" y1="10"  x2="210" y2="410" stroke="white" strokeWidth="0.75"/>
        </svg>
      </div>

      {/* ── Form panel ── */}
      <div className="intake-form-panel">
        <div className="intake-form-inner">
          <h1 className="intake-form-heading">Get started</h1>
          <p className="intake-form-sub">
            We need a few details before connecting you with your care team.
          </p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="intake-field">
              <label htmlFor="firstName">First name</label>
              <input
                id="firstName"
                type="text"
                placeholder="Jane"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                autoComplete="given-name"
              />
            </div>

            <div className="intake-field">
              <label htmlFor="lastName">Last name</label>
              <input
                id="lastName"
                type="text"
                placeholder="Smith"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                autoComplete="family-name"
              />
            </div>

            <div className="intake-field">
              <label htmlFor="dob">Date of birth</label>
              <input
                id="dob"
                type="date"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                autoComplete="bday"
              />
            </div>

            <div className="intake-field">
              <label htmlFor="phone">Phone number</label>
              <input
                id="phone"
                type="tel"
                placeholder="+1 (555) 000-0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                autoComplete="tel"
              />
            </div>

            <div className="intake-field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                placeholder="jane@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>

            <div className="intake-toggle-row">
              <div className="intake-toggle-text">
                SMS appointment reminders
                <small>Opt in to receive a text before your visit</small>
              </div>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={smsOptIn}
                  onChange={(e) => setSmsOptIn(e.target.checked)}
                />
                <span className="toggle-track" />
              </label>
            </div>

            <button
              type="submit"
              className="intake-submit"
              disabled={loading}
            >
              {loading ? "Connecting…" : "Continue to chat"}
            </button>

            {error && <p className="intake-error">{error}</p>}
          </form>
        </div>
      </div>
    </div>
  );
}
