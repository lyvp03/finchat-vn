"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PriceHistoryResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

import { DashboardMode, AVAILABLE_ASSETS } from "./dashboard-toolbar";

interface TechnicalIndicatorsProps {
  historyData: PriceHistoryResponse;
  mode?: DashboardMode;
  compareHistories?: PriceHistoryResponse[];
}

export function TechnicalIndicators({ historyData, mode = "single", compareHistories = [] }: TechnicalIndicatorsProps) {
  const { rsi14, rsi_summary, top_moves, metadata } = historyData;

  const getRsiColor = (val: number) => {
    if (val >= 70) return "bg-red-500";
    if (val <= 30) return "bg-emerald-500";
    return "bg-amber-500";
  };

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val);

  return (
    <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
              Phân tích kỹ thuật
            </CardTitle>
            <CardDescription className="mt-1">
              Chỉ báo chính cho {AVAILABLE_ASSETS.find(a => a.id === historyData.type_code)?.name || metadata.name}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6 pt-4 flex-1">
        
        {/* RSI Indicator */}
        <div className="space-y-2 bg-background/50 p-4 rounded-xl border border-border/50 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-muted-foreground">RSI (14 ngày)</span>
            <Badge variant={rsi14 >= 70 ? "destructive" : rsi14 <= 30 ? "default" : "secondary"}
              className={rsi14 <= 30 ? "bg-positive hover:bg-positive/90 text-white" : ""}
            >
              {rsi_summary.toUpperCase()}
            </Badge>
          </div>
          <div className="relative pt-2">
            <Progress value={rsi14} className="h-1.5" indicatorClassName={getRsiColor(rsi14)} />
            <div className="flex justify-between text-[10px] text-muted-foreground font-medium mt-2 uppercase tracking-wider">
              <span>0 (Quá bán)</span>
              <span>100 (Quá mua)</span>
            </div>
            {/* RSI Marker */}
            <div 
              className="absolute top-1 w-1.5 h-3.5 bg-foreground rounded-full shadow-[0_0_8px_rgba(255,255,255,0.5)] -ml-[3px]"
              style={{ left: `${Math.min(100, Math.max(0, rsi14))}%` }}
            />
          </div>
          <div className="text-center text-4xl font-bold tracking-tight mt-4 tabular-nums">
            {rsi14.toFixed(1)}
          </div>
        </div>

        {mode === "compare" && compareHistories.length > 0 ? (
          <div className="space-y-3">
            <h4 className="text-base font-semibold text-foreground">So sánh chỉ báo</h4>
            <div className="rounded-lg border border-border/50 overflow-hidden">
              <table className="w-full text-base">
                <thead className="bg-muted/50 text-sm uppercase text-foreground/80">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold">Tài sản</th>
                    <th className="px-3 py-2 text-right font-semibold">RSI</th>
                    <th className="px-3 py-2 text-right font-semibold">Tín hiệu</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50 bg-background/30">
                  {compareHistories.map((ch) => (
                    <tr key={ch.type_code} className="hover:bg-muted/30 transition-colors">
                      <td className="px-3 py-2 font-medium text-foreground">
                        {ch.metadata.market} {ch.type_code.replace(ch.metadata.market, '')}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        {ch.rsi14.toFixed(1)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <span className={`text-xs px-2 py-1 rounded uppercase font-semibold tracking-wider ${
                          ch.rsi14 >= 70 ? 'bg-destructive/10 text-destructive' : 
                          ch.rsi14 <= 30 ? 'bg-positive/10 text-positive' : 'bg-muted text-muted-foreground'
                        }`}>
                          {ch.rsi_summary}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="space-y-3 pt-2">
            <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500"><path d="M12 2v20"/><path d="m17 7-5-5-5 5"/><path d="m17 17-5 5-5-5"/></svg>
              Top biến động mạnh
            </h4>
            <div className="space-y-2">
              {top_moves.slice(0, 3).map((move, i) => {
                const isPositive = move.price_change > 0;
                return (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-background/50 border border-border/50 hover:border-border transition-colors">
                    <div className="text-sm font-medium text-muted-foreground">
                      {new Date(move.ts).toLocaleDateString("vi-VN", { month: "short", day: "numeric" })}
                    </div>
                    <div className="text-sm font-semibold tabular-nums">
                      {formatCurrency(move.mid_price)}
                    </div>
                    <div className={`text-sm font-bold tabular-nums flex items-center gap-1 ${isPositive ? 'text-positive' : 'text-negative'}`}>
                      {isPositive ? "+" : ""}{formatCurrency(move.price_change)}
                    </div>
                  </div>
                );
              })}
              {top_moves.length === 0 && (
                <div className="text-sm text-muted-foreground text-center py-4 bg-background/50 rounded-lg border border-border/50 border-dashed">
                  Không có dữ liệu biến động
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
