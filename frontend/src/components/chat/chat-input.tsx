"use client";

import { useState, KeyboardEvent, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SendHorizonal } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-4 bg-background/80 backdrop-blur-xl relative z-10 border-t border-border/50">
      <div className="max-w-3xl mx-auto relative flex items-end gap-2 bg-card p-2 rounded-2xl border border-border/50 shadow-sm focus-within:ring-1 focus-within:ring-primary/50 focus-within:border-primary/50 transition-all">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Hỏi về giá vàng, tin tức, xu hướng..."
          className="min-h-[44px] max-h-[200px] resize-none border-0 focus-visible:ring-0 bg-transparent shadow-none px-3 py-3 text-base"
          disabled={isLoading}
          rows={1}
        />
        <Button 
          size="icon" 
          className="h-[44px] w-[44px] rounded-xl shrink-0 bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm transition-transform active:scale-95"
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
        >
          <SendHorizonal className="h-5 w-5" />
          <span className="sr-only">Gửi</span>
        </Button>
      </div>
      <div className="max-w-3xl mx-auto text-center mt-3">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          AI có thể mắc lỗi. Vui lòng kiểm chứng thông tin.
        </span>
      </div>
    </div>
  );
}
