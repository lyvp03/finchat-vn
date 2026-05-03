import { useState, useCallback } from "react";
import { fetchAPI } from "@/lib/api";
import { ChatResponse, EvalResponse, EvalScores } from "@/lib/types";

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  intent?: string;
  sources?: unknown;
  eval?: EvalScores | null;
  evalLoading?: boolean;
  /** The user question that triggered this assistant response */
  questionRef?: string;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // Keep only last 6 messages for context
      const history = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetchAPI<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: content, history }),
      });

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.response,
        intent: response.intent,
        sources: response.sources,
        questionRef: content,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Chat error:", err);
      setError("Không thể kết nối đến máy chủ. Vui lòng thử lại sau.");
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Xin lỗi, đã xảy ra lỗi khi kết nối với hệ thống. Vui lòng thử lại.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const evaluateMessage = useCallback(async (messageId: string) => {
    const msg = messages.find((m) => m.id === messageId);
    if (!msg || msg.role !== "assistant" || !msg.questionRef) return;

    // Mark as loading
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, evalLoading: true } : m))
    );

    try {
      const result = await fetchAPI<EvalResponse>("/api/chat/evaluate", {
        method: "POST",
        body: JSON.stringify({
          question: msg.questionRef,
          answer: msg.content,
        }),
      });

      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? { ...m, eval: result.ok ? result.scores! : null, evalLoading: false }
            : m
        )
      );
    } catch (err) {
      console.error("Eval error:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? { ...m, eval: null, evalLoading: false } : m
        )
      );
    }
  }, [messages]);

  const retryMessage = useCallback(async (messageId: string) => {
    const msg = messages.find((m) => m.id === messageId);
    if (!msg || msg.role !== "assistant" || !msg.questionRef) return;

    // Remove the old assistant message
    setMessages((prev) => prev.filter((m) => m.id !== messageId));

    // Re-send the original question
    setIsLoading(true);
    setError(null);

    try {
      const history = messages
        .filter((m) => m.id !== messageId)
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await fetchAPI<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: msg.questionRef, history }),
      });

      const newMessage: ChatMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: response.response,
        intent: response.intent,
        sources: response.sources,
        questionRef: msg.questionRef,
      };

      setMessages((prev) => [...prev, newMessage]);
    } catch (err) {
      console.error("Retry error:", err);
      setError("Không thể kết nối. Vui lòng thử lại.");
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: "Xin lỗi, đã xảy ra lỗi khi thử lại. Vui lòng thử lại sau.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    evaluateMessage,
    retryMessage,
  };
}
