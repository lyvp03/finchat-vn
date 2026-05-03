"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { ChatMessage } from "@/hooks/use-chat";
import { User, Bot } from "lucide-react";
import { TypingRenderer, StreamCursor } from "./typing-renderer";
import { ThinkingIndicator } from "./thinking-indicator";
import { MessageActions } from "./message-actions";
import { EvalScoreCard } from "./eval-score-card";
import { FinancialMarkdown } from "./financial-markdown";

interface ChatMessagesProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onEvaluate?: (messageId: string) => void;
  onRetry?: (messageId: string) => void;
  onFollowUp?: (prompt: string) => void;
}

export function ChatMessages({
  messages,
  isLoading,
  onEvaluate,
  onRetry,
  onFollowUp,
}: ChatMessagesProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [typingDone, setTypingDone] = useState<Set<string>>(new Set());

  const scrollToBottom = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el || !autoScroll) return;
    el.scrollTop = el.scrollHeight;
  }, [autoScroll]);

  // Detect user scrolling up → pause auto-scroll
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setAutoScroll(distanceFromBottom < 80);
  }, []);

  // Force scroll when new message arrives
  useEffect(() => {
    setAutoScroll(true);
    setTimeout(() => {
      const el = scrollContainerRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    }, 50);
  }, [messages.length]);

  // Scroll during typing / loading
  useEffect(() => {
    if (!autoScroll) return;
    const interval = setInterval(() => {
      const el = scrollContainerRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    }, 300);
    return () => clearInterval(interval);
  }, [autoScroll]);

  // Scroll on loading state change
  useEffect(() => {
    if (isLoading) {
      setAutoScroll(true);
      setTimeout(() => {
        const el = scrollContainerRef.current;
        if (el) el.scrollTop = el.scrollHeight;
      }, 50);
    }
  }, [isLoading]);

  const handleTypingComplete = useCallback((messageId: string) => {
    setTypingDone((prev) => new Set(prev).add(messageId));
  }, []);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
        <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
          <Bot className="h-7 w-7 text-primary" />
        </div>
        <h3 className="text-lg font-semibold text-foreground">Trợ lý phân tích vàng</h3>
        <p className="max-w-md mt-2 text-xs leading-relaxed">
          Hỏi về giá vàng SJC, DOJI, XAU/USD, tin tức thị trường, hoặc yêu cầu phân tích xu hướng.
        </p>
      </div>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto p-3"
    >
      <div className="space-y-4 pb-4">
        {messages.map((message) => {
          const isAssistant = message.role === "assistant";
          const hasFinishedTyping = typingDone.has(message.id);

          return (
            <div
              key={message.id}
              className={`flex gap-2.5 ${
                isAssistant ? "justify-start" : "justify-end"
              } animate-in fade-in slide-in-from-bottom-2 duration-300`}
            >
              {/* Avatar */}
              {isAssistant && (
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary flex items-center justify-center mt-1">
                  <Bot className="h-3 w-3 text-primary-foreground" />
                </div>
              )}

              {/* Message content */}
              <div className={`${isAssistant ? "max-w-[92%]" : "max-w-[75%]"}`}>
                <div
                  className={`rounded-2xl px-3.5 py-2 border ${
                    isAssistant
                      ? "bg-muted/20 border-border/50 text-foreground rounded-bl-none"
                      : "bg-card border-border/50 text-foreground rounded-br-none shadow-sm"
                  }`}
                >
                  {!isAssistant ? (
                    <div className="whitespace-pre-wrap text-[15px]">{message.content}</div>
                  ) : (
                    <TypingRenderer
                      content={message.content}
                      charsPerTick={8}
                      intervalMs={20}
                      onComplete={() => handleTypingComplete(message.id)}
                    >
                      {(revealedText, isDone) => (
                        <>
                          <FinancialMarkdown content={revealedText} />
                          {!isDone && <StreamCursor />}
                        </>
                      )}
                    </TypingRenderer>
                  )}
                </div>

                {/* Actions + Eval — only show after typing finishes */}
                {isAssistant && hasFinishedTyping && (
                  <div className="animate-in fade-in duration-300">
                    <MessageActions
                      content={message.content}
                      onRetry={onRetry ? () => onRetry(message.id) : undefined}
                      onFollowUp={onFollowUp}
                    />
                    {message.questionRef && (
                      <EvalScoreCard
                        scores={message.eval}
                        isLoading={message.evalLoading}
                        onEvaluate={() => onEvaluate?.(message.id)}
                      />
                    )}
                  </div>
                )}
              </div>

              {/* User avatar */}
              {!isAssistant && (
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-secondary border border-border/50 flex items-center justify-center mt-1">
                  <User className="h-3 w-3 text-secondary-foreground" />
                </div>
              )}
            </div>
          );
        })}

        {/* Thinking indicator */}
        {isLoading && <ThinkingIndicator />}
      </div>
    </div>
  );
}
