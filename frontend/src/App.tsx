import { useEffect, useState } from "react";
import { useSession } from "./hooks/useSession";
import ErrorBoundary from "./components/ErrorBoundary";
import IntakeForm from "./components/IntakeForm";
import ChatWindow from "./components/ChatWindow";
import AdminDashboard from "./components/AdminDashboard";

export default function App() {
  const { sessionId, patientId, saveSession } = useSession();
  const [isAdmin, setIsAdmin] = useState(() => window.location.hash === "#admin");

  useEffect(() => {
    const onHash = () => setIsAdmin(window.location.hash === "#admin");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
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

  if (!sessionId || !patientId) {
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
