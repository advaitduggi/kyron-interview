import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useChat } from "../hooks/useChat";
import VoiceButton from "./VoiceButton";

interface Props {
  sessionId: string;
  patientId: string;
  onSessionUpdate: (sessionId: string) => void;
}

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function ChatWindow({ sessionId, patientId, onSessionUpdate }: Props) {
  const { messages, streamingContent, isLoading, sendMessage } = useChat({
    sessionId,
    patientId,
    onSessionUpdate,
  });
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  // auto-scroll whenever messages or streaming content change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  function handleSend() {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    void sendMessage(text);
  }

  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const showTypingDots = isLoading && streamingContent === "";
  const showStreaming  = isLoading && streamingContent !== null && streamingContent !== "";

  return (
    <div className="chat-root">
      {/* ── Header ── */}
      <header className="chat-header">
        <span className="chat-wordmark">Kyron</span>
        <VoiceButton sessionId={sessionId} patientId={patientId} />
      </header>

      {/* ── Messages ── */}
      <div className="chat-messages">
        {messages.length === 0 && !isLoading && (
          <div className="chat-empty">
            <p className="chat-empty-title">How can I help you today?</p>
            <p className="chat-empty-sub">
              Describe your concern and I will connect you with the right specialist.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`msg-row ${msg.role === "user" ? "msg-row-user" : "msg-row-assistant"}`}
          >
            {msg.role === "assistant" && (
              <div className="msg-avatar" aria-hidden="true">K</div>
            )}
            <div className="msg-body">
              <div
                className={`msg-bubble ${
                  msg.role === "user" ? "msg-bubble-user" : "msg-bubble-assistant"
                }`}
              >
                {msg.content}
              </div>
              <span className="msg-time">{formatTime(msg.timestamp)}</span>
            </div>
          </div>
        ))}

        {/* streaming bubble */}
        {showStreaming && (
          <div className="msg-row msg-row-assistant">
            <div className="msg-avatar" aria-hidden="true">K</div>
            <div className="msg-body">
              <div className="msg-bubble-streaming">{streamingContent}</div>
            </div>
          </div>
        )}

        {/* typing indicator */}
        {showTypingDots && (
          <div className="typing-row">
            <div className="msg-avatar" aria-hidden="true">K</div>
            <div className="typing-bubble">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div className="chat-bar">
        <input
          ref={inputRef}
          className="chat-input"
          type="text"
          placeholder="Type your message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={isLoading}
          autoComplete="off"
        />
        <button
          className="chat-send"
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          aria-label="Send message"
          type="button"
        >
          {/* send arrow */}
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
