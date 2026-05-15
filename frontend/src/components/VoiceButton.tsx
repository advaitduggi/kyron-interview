import { useState } from "react";

export default function VoiceButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button className="voice-btn" onClick={() => setOpen(true)} type="button">
        {/* phone outline SVG */}
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
        Voice call
      </button>

      {open && (
        <div
          className="modal-backdrop"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Voice call"
        >
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-icon-wrap">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.7 12.5 19.79 19.79 0 0 1 1.64 3.89 2 2 0 0 1 3.61 2H6.5a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L7.5 9.59a16 16 0 0 0 6 6l.75-.75a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" />
              </svg>
            </div>
            <h2 className="modal-title">Voice call coming soon</h2>
            <p className="modal-body">
              This feature will let you continue your conversation by phone.
              A care navigator will pick up with full context of your chat.
            </p>
            <button className="modal-close" onClick={() => setOpen(false)}>
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  );
}
