import { useState, useCallback, useRef } from "react";
import { fetchAPI } from "@/lib/api";
import { ChatResponse, EvalResponse, EvalScores, MessageStatus, ApiError } from "@/lib/types";

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  intent?: string;
  sources?: unknown;
  eval?: EvalScores | null;
  evalLoading?: boolean;
  /** The user question that triggered this assistant response */
  questionRef?: string;
  errorMessage?: string;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastSubmitTimeRef = useRef<number>(0);

  const runChatRequest = async (question: string, history: Array<{ role: string; content: string }>) => {
    // 1. Cancel previous request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    const assistantMsgId = (Date.now() + 1).toString();
    
    // 2. Add/Reset assistant placeholder
    setMessages((prev) => {
      const filtered = prev.filter(m => m.status !== "error" || m.questionRef !== question);
      return [
        ...filtered,
        {
          id: assistantMsgId,
          role: "assistant",
          content: "",
          status: "pending",
          questionRef: question,
        }
      ];
    });

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchAPI<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: question, history }),
        signal: abortControllerRef.current.signal,
      });

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: response.response,
                status: "streaming", // TypingRenderer will pick this up
                intent: response.intent,
                sources: response.sources,
              }
            : m
        )
      );
    } catch (err: any) {
      if (err.status === 408 || (err instanceof DOMException && err.name === "AbortError")) {
        // Silently handle manual aborts unless needed
        return;
      }
      
      const apiErr = err as ApiError;
      console.error("Chat error:", apiErr);
      
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                status: "error",
                errorMessage: apiErr.message || "Lỗi kết nối máy chủ.",
                content: "Xin lỗi, đã xảy ra lỗi khi kết nối với hệ thống. Vui lòng thử lại.",
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const sendMessage = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || isLoading) return;

    // Rate limit: 800ms
    const now = Date.now();
    if (now - lastSubmitTimeRef.current < 800) return;
    lastSubmitTimeRef.current = now;

    // Length limit: 4000
    if (trimmed.length > 4000) {
      setError("Câu hỏi quá dài (tối đa 4000 ký tự).");
      return;
    }

    const userMessage: ChatMessage = {
      id: now.toString(),
      role: "user",
      content: trimmed,
      status: "done",
    };

    const history = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    setMessages((prev) => [...prev, userMessage]);
    await runChatRequest(trimmed, history);
  };

  const evaluateMessage = useCallback(async (messageId: string) => {
    const msg = messages.find((m) => m.id === messageId);
    if (!msg || msg.role !== "assistant" || !msg.questionRef || msg.status !== "done") return;

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

    const history = messages
      .filter((m) => m.id !== messageId)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));

    await runChatRequest(msg.questionRef, history);
  }, [messages]);

  const clearChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    evaluateMessage,
    retryMessage,
    clearChat,
    setMessages, // For TypingRenderer completion
  };
}
