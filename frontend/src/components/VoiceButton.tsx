import { useState } from "react";
import { initiateCall } from "../lib/api";

type CallState = "idle" | "calling" | "success" | "error";

const PhoneIcon = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.75"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.7 12.5 19.79 19.79 0 0 1 1.64 3.89 2 2 0 0 1 3.61 2H6.5a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L7.5 9.59a16 16 0 0 0 6 6l.75-.75a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" />
  </svg>
);

interface VoiceButtonProps {
  sessionId: string | null;
  patientId: string | null;
  patientPhone?: string | null;
}

export default function VoiceButton({ sessionId, patientId, patientPhone }: VoiceButtonProps) {
  const [callState, setCallState] = useState<CallState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const disabled = !sessionId || !patientId || callState === "calling" || callState === "success";

  async function handleClick() {
    if (!sessionId || !patientId) return;
    setCallState("calling");
    setErrorMsg(null);
    try {
      await initiateCall(sessionId, patientId);
      setCallState("success");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to initiate call");
      setCallState("error");
    }
  }

  const displayPhone = patientPhone
    ? patientPhone.replace(/^\+?1?(\d{3})(\d{3})(\d{4})$/, "+1 ($1) $2-$3") || patientPhone
    : "your phone";

  return (
    <div className="voice-btn-wrap">
      <button
        className={`voice-btn${callState === "calling" ? " voice-btn--calling" : ""}${callState === "success" ? " voice-btn--success" : ""}`}
        onClick={() => void handleClick()}
        type="button"
        disabled={disabled}
        aria-label="Start voice call"
      >
        <PhoneIcon />
        {callState === "calling" ? "Calling…" : callState === "success" ? "Call placed" : "Voice call"}
      </button>

      {callState === "calling" && (
        <p className="voice-status voice-status--calling">Calling your phone…</p>
      )}
      {callState === "success" && (
        <p className="voice-status voice-status--success">
          Call incoming to {displayPhone}. The AI has your full context.
        </p>
      )}
      {callState === "error" && errorMsg && (
        <p className="voice-status voice-status--error">{errorMsg}</p>
      )}
    </div>
  );
}
