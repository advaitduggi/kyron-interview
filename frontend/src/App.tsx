import { useEffect, useState } from "react";
import { useSession } from "./hooks/useSession";
import { getSession } from "./lib/api";

const isValidUUID = (id: string) =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
import ErrorBoundary from "./components/ErrorBoundary";
import IntakeForm from "./components/IntakeForm";
import ChatWindow from "./components/ChatWindow";
import AdminDashboard from "./components/AdminDashboard";

export default function App() {
  const { sessionId, patientId, saveSession, clearSession } = useSession();
  const [isAdmin, setIsAdmin] = useState(() => window.location.hash === "#admin");
  // null = still validating, true = valid, false = invalid/expired
  const [sessionValid, setSessionValid] = useState<boolean | null>(
    sessionId ? null : true
  );

  useEffect(() => {
    const onHash = () => setIsAdmin(window.location.hash === "#admin");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Validate the stored session against the server on mount.
  // Also check that patientId is a well-formed UUID — a non-UUID value (e.g.
  // a process PID that leaked into localStorage) would cause FK violations.
  // Clear and drop to intake on any validation failure.
  useEffect(() => {
    if (!sessionId) return;
    if (patientId && !isValidUUID(patientId)) {
      clearSession();
      setSessionValid(false);
      return;
    }
    getSession(sessionId)
      .then(() => setSessionValid(true))
      .catch(() => {
        clearSession();
        setSessionValid(false);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isAdmin) {
    return (
      <div className="app-fade" style={{ height: "100%" }}>
        <ErrorBoundary>
          <AdminDashboard />
        </ErrorBoundary>
      </div>
    );
  }

  // Still pinging the server to check if the cached session is alive
  if (sessionValid === null) {
    return null;
  }

  if (!sessionId || !patientId || !sessionValid) {
    return (
      <div className="app-fade" style={{ height: "100%" }}>
        <ErrorBoundary>
          <IntakeForm
            onComplete={(pid, sid) => saveSession(sid, pid)}
          />
        </ErrorBoundary>
      </div>
    );
  }

  return (
    <div className="app-fade" style={{ height: "100%" }}>
      <ErrorBoundary>
        <ChatWindow
          sessionId={sessionId}
          patientId={patientId}
          onSessionUpdate={(sid) => saveSession(sid, patientId)}
        />
      </ErrorBoundary>
    </div>
  );
}
