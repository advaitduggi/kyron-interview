import { useState, useRef, useCallback } from "react";
import * as api from "../lib/api";

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface UseChatOptions {
  sessionId: string;
  patientId: string | null;
  onSessionUpdate: (sessionId: string) => void;
}

export function useChat({ sessionId, patientId, onSessionUpdate }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const loadingRef = useRef(false); // guard against concurrent sends

  const sendMessage = useCallback(
    async (text: string) => {
      if (loadingRef.current) return;
      loadingRef.current = true;
      setIsLoading(true);

      const userMsg: Message = { role: "user", content: text, timestamp: new Date() };
      setMessages((prev) => [...prev, userMsg]);
      setStreamingContent(""); // empty string = show typing indicator

      let accumulated = "";

      try {
        for await (const event of api.sendMessage(sessionId, patientId, text)) {
          if (event.type === "text_delta") {
            accumulated += event.text;
            setStreamingContent(accumulated);
          } else if (event.type === "end") {
            onSessionUpdate(event.session_id);
          }
        }
        // Finalise: move streamed content into messages list
        if (accumulated) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: accumulated, timestamp: new Date() },
          ]);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Something went wrong. Please try again.",
            timestamp: new Date(),
          },
        ]);
      } finally {
        setStreamingContent(null);
        setIsLoading(false);
        loadingRef.current = false;
      }
    },
    [sessionId, patientId, onSessionUpdate]
  );

  return { messages, streamingContent, isLoading, sendMessage };
}
