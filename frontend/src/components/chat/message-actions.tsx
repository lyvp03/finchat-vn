"use client";

import { useState } from "react";
import { Copy, Check, RefreshCw, MessageSquarePlus } from "lucide-react";
import { Button } from "@/components/ui/button";

const FOLLOW_UP_SUGGESTIONS = [
  "Phân tích chi tiết hơn",
  "Vì sao lại như vậy?",
  "So sánh với tuần trước",
  "Tin tức liên quan?",
];

interface MessageActionsProps {
  content: string;
  onRetry?: () => void;
  onFollowUp?: (prompt: string) => void;
}

export function MessageActions({ content, onRetry, onFollowUp }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [showFollowUps, setShowFollowUps] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement("textarea");
      textarea.value = content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="mt-2 space-y-2">
      {/* Action buttons */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1.5"
          onClick={handleCopy}
        >
          {copied ? (
            <><Check className="h-3 w-3 text-emerald-500" /> Đã copy</>
          ) : (
            <><Copy className="h-3 w-3" /> Copy</>
          )}
        </Button>

        {onRetry && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1.5"
            onClick={onRetry}
          >
            <RefreshCw className="h-3 w-3" /> Thử lại
          </Button>
        )}

        {onFollowUp && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1.5"
            onClick={() => setShowFollowUps(!showFollowUps)}
          >
            <MessageSquarePlus className="h-3 w-3" /> Hỏi tiếp
          </Button>
        )}
      </div>

      {/* Follow-up suggestion chips */}
      {showFollowUps && onFollowUp && (
        <div className="flex flex-wrap gap-1.5 animate-in fade-in slide-in-from-top-1 duration-200">
          {FOLLOW_UP_SUGGESTIONS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => {
                onFollowUp(prompt);
                setShowFollowUps(false);
              }}
              className="text-xs px-2.5 py-1 rounded-full border border-border/50 bg-background/50 text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/5 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
