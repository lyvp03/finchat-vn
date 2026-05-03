"use client";

import { useState, useEffect } from "react";
import { Bot, Database, Newspaper, Sparkles } from "lucide-react";

const THINKING_STEPS = [
  { icon: Database, label: "Đang truy vấn dữ liệu giá vàng...", delay: 0 },
  { icon: Newspaper, label: "Đang tìm kiếm tin tức liên quan...", delay: 1200 },
  { icon: Sparkles, label: "Đang phân tích và tổng hợp...", delay: 2800 },
];

export function ThinkingIndicator() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timers = THINKING_STEPS.map((step, index) => {
      if (index === 0) return null;
      return setTimeout(() => setActiveStep(index), step.delay);
    });

    return () => timers.forEach((t) => t && clearTimeout(t));
  }, []);

  return (
    <div className="flex gap-4 justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="bg-muted/30 border border-border/50 rounded-2xl rounded-bl-none px-5 py-4 shadow-sm max-w-xs">
        <div className="space-y-2.5">
          {THINKING_STEPS.map((step, index) => {
            const Icon = step.icon;
            const isActive = index <= activeStep;
            const isCurrent = index === activeStep;

            return (
              <div
                key={index}
                className={`flex items-center gap-2.5 transition-all duration-500 ${
                  isActive
                    ? "opacity-100 translate-y-0"
                    : "opacity-0 translate-y-1 h-0 overflow-hidden"
                }`}
              >
                <div className={`p-1 rounded-md ${isCurrent ? "bg-primary/10" : "bg-muted/50"}`}>
                  <Icon className={`h-3.5 w-3.5 ${isCurrent ? "text-primary animate-pulse" : "text-muted-foreground"}`} />
                </div>
                <span className={`text-sm ${isCurrent ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                  {step.label}
                </span>
                {isCurrent && (
                  <div className="flex gap-1 ml-1">
                    <div className="w-1 h-1 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-1 h-1 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-1 h-1 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
