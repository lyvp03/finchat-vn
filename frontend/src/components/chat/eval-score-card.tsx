"use client";

import { EvalScores } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Sparkles, Loader2 } from "lucide-react";

interface EvalScoreCardProps {
  scores: EvalScores | null | undefined;
  isLoading?: boolean;
  onEvaluate?: () => void;
}

const CRITERIA = [
  { key: "correctness", label: "Correctness", weight: "30%", icon: "🎯" },
  { key: "insight", label: "Insight", weight: "25%", icon: "💡" },
  { key: "naturalness", label: "Naturalness", weight: "20%", icon: "🗣️" },
  { key: "clarity", label: "Clarity", weight: "15%", icon: "📖" },
  { key: "conciseness", label: "Conciseness", weight: "10%", icon: "✂️" },
] as const;

function getVerdict(score: number) {
  if (score >= 4.5) return { label: "Production-ready", color: "text-orange-400", bg: "bg-orange-400/10", emoji: "🔥" };
  if (score >= 3.8) return { label: "Tốt", color: "text-emerald-500", bg: "bg-emerald-500/10", emoji: "✅" };
  if (score >= 3.0) return { label: "Trung bình", color: "text-amber-500", bg: "bg-amber-500/10", emoji: "⚠️" };
  return { label: "Fail", color: "text-red-500", bg: "bg-red-500/10", emoji: "❌" };
}

function getBarColor(score: number) {
  if (score >= 4) return "bg-emerald-500";
  if (score >= 3) return "bg-amber-500";
  return "bg-red-500";
}

export function EvalScoreCard({ scores, isLoading, onEvaluate }: EvalScoreCardProps) {
  // Not yet evaluated → show trigger button
  if (!scores && !isLoading) {
    return (
      <button
        onClick={onEvaluate}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors mt-2 px-3 py-1.5 rounded-lg border border-border/50 hover:border-primary/30 hover:bg-primary/5"
      >
        <Sparkles className="h-3.5 w-3.5" />
        Auto-eval
      </button>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-2 px-3 py-2 rounded-lg border border-border/50 bg-muted/20 animate-pulse">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Đang chấm điểm...
      </div>
    );
  }

  if (!scores) return null;

  const verdict = getVerdict(scores.final_score);

  return (
    <div className="mt-3 rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm overflow-hidden text-sm max-w-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/40 bg-muted/20">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <Sparkles className="h-4 w-4 text-primary" />
          Auto-eval
        </div>
        <Badge
          variant="outline"
          className={`text-xs font-semibold ${verdict.color} ${verdict.bg} border-0`}
        >
          {verdict.emoji} {scores.final_score.toFixed(2)} — {verdict.label}
        </Badge>
      </div>

      {/* Scores */}
      <div className="px-4 py-3 space-y-2.5">
        {CRITERIA.map(({ key, label, weight, icon }) => {
          const val = scores[key];
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="text-xs w-4 text-center">{icon}</span>
              <span className="text-xs text-muted-foreground w-24 truncate">
                {label} <span className="text-muted-foreground/60">({weight})</span>
              </span>
              <div className="flex-1">
                <Progress
                  value={(val / 5) * 100}
                  className="h-1.5"
                  indicatorClassName={getBarColor(val)}
                />
              </div>
              <span className="text-xs font-semibold tabular-nums w-6 text-right">
                {val.toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
