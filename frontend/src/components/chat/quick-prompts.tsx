"use client";

import { Sparkles } from "lucide-react";

interface QuickPromptsProps {
  onSelect: (prompt: string) => void;
}

const PROMPTS = [
  { emoji: "💰", text: "Giá vàng SJC hôm nay thế nào?" },
  { emoji: "📉", text: "Vì sao giá vàng giảm gần đây?" },
  { emoji: "📊", text: "So sánh giá vàng tháng này với tháng trước" },
  { emoji: "📰", text: "Tin nào ảnh hưởng mạnh nhất đến vàng?" },
];

export function QuickPrompts({ onSelect }: QuickPromptsProps) {
  return (
    <div className="max-w-2xl mx-auto px-4 mb-4">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-3 justify-center">
        <Sparkles className="h-3.5 w-3.5" />
        <span>Gợi ý câu hỏi</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt.text}
            onClick={() => onSelect(prompt.text)}
            className="flex items-center gap-2.5 text-left px-4 py-3 rounded-xl border border-border/50 bg-card/50 hover:bg-card hover:border-primary/30 hover:shadow-sm transition-all text-sm text-muted-foreground hover:text-foreground group"
          >
            <span className="text-base group-hover:scale-110 transition-transform">{prompt.emoji}</span>
            <span>{prompt.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
