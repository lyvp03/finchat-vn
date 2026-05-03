"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NewsSummaryResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownRight, Minus, Newspaper, BarChart3, TrendingUp } from "lucide-react";

interface NewsKpiSummaryProps {
  summary: NewsSummaryResponse;
}

export function NewsKpiSummary({ summary }: NewsKpiSummaryProps) {
  const isPositiveSentiment = summary.avg_sentiment > 0.05;
  const isNegativeSentiment = summary.avg_sentiment < -0.05;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Tổng Tin Tức ({summary.days} ngày)</CardTitle>
          <div className="p-2 bg-blue-500/10 rounded-lg">
            <Newspaper className="h-4 w-4 text-blue-500" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight">{summary.total} bài</div>
          <div className="mt-3 flex flex-wrap gap-1">
            {summary.count_by_scope.map((scope) => (
              <Badge key={scope.market_scope} variant="secondary" className="text-xs">
                {scope.market_scope === "domestic" ? "Trong nước" : "Quốc tế"}: {scope.count}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Tín Hiệu AI (Sentiment)</CardTitle>
          <div className={`p-2 rounded-lg ${isPositiveSentiment ? 'bg-positive/10' : isNegativeSentiment ? 'bg-negative/10' : 'bg-muted'}`}>
            {isPositiveSentiment ? <ArrowUpRight className="h-4 w-4 text-positive" /> :
              isNegativeSentiment ? <ArrowDownRight className="h-4 w-4 text-negative" /> :
                <Minus className="h-4 w-4 text-muted-foreground" />}
          </div>
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold tracking-tight ${isPositiveSentiment ? 'text-positive' : isNegativeSentiment ? 'text-negative' : ''}`}>
            {summary.avg_sentiment > 0 ? "+" : ""}{(summary.avg_sentiment * 100).toFixed(1)}%
          </div>
          <p className="text-xs text-muted-foreground mt-1 font-medium">Trung bình {summary.days} ngày qua</p>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Mức Độ Ảnh Hưởng (Impact)</CardTitle>
          <div className="p-2 bg-purple-500/10 rounded-lg">
            <TrendingUp className="h-4 w-4 text-purple-500" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight">{(summary.avg_impact * 100).toFixed(1)}%</div>
          <div className="mt-3 flex flex-wrap gap-1">
            <span className="text-xs text-muted-foreground mr-1">Chủ đề:</span>
            {summary.top_event_types.slice(0, 2).map((event) => (
              <Badge key={event.event_type} variant="outline" className="text-xs font-normal border-border/50">
                {event.event_type.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
