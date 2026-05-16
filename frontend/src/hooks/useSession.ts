import { useState } from "react";

const KEY_SESSION = "kyron_session_id";
const KEY_PATIENT = "kyron_patient_id";

const isUUID = (s: string) =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(
    () => localStorage.getItem(KEY_SESSION)
  );
  const [patientId, setPatientId] = useState<string | null>(
    () => localStorage.getItem(KEY_PATIENT)
  );

  function saveSession(sid: string, pid: string) {
    if (!isUUID(sid) || !isUUID(pid)) {
      console.error(
        `saveSession: refusing to store non-UUID values — session_id="${sid}" patient_id="${pid}"`
      );
      return;
    }
    localStorage.setItem(KEY_SESSION, sid);
    localStorage.setItem(KEY_PATIENT, pid);
    setSessionId(sid);
    setPatientId(pid);
  }

  function clearSession() {
    localStorage.removeItem(KEY_SESSION);
    localStorage.removeItem(KEY_PATIENT);
    setSessionId(null);
    setPatientId(null);
  }

  return { sessionId, patientId, saveSession, clearSession };
}
