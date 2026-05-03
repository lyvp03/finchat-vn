"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PriceData } from "@/lib/types";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { DashboardMode, AVAILABLE_ASSETS } from "./dashboard-toolbar";
import { Badge } from "@/components/ui/badge";

interface KPICardsProps {
  priceData: PriceData;
  mode?: DashboardMode;
  compareData?: PriceData[];
}

export function KPICards({ priceData, mode = "single", compareData = [] }: KPICardsProps) {
  const { buy_price, sell_price, spread, daily_return_pct, metadata } = priceData;

  const formatCurrency = (val: number, unit: string) => {
    if (unit === 'USD/oz') {
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
    }
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val);
  };

  const isPositive = daily_return_pct > 0;
  const isNegative = daily_return_pct < 0;

  const assetName = AVAILABLE_ASSETS.find(a => a.id === priceData.type_code)?.name || metadata.name;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{assetName} Mua vào</CardTitle>
          <div className="p-2 bg-amber-500/10 rounded-lg">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" className="h-4 w-4 text-amber-500">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight">{formatCurrency(buy_price, metadata.unit)}</div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{assetName} Bán ra</CardTitle>
          <div className="p-2 bg-amber-500/10 rounded-lg">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" className="h-4 w-4 text-amber-500">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight">{formatCurrency(sell_price, metadata.unit)}</div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Thay đổi %</CardTitle>
          <div className={`p-2 rounded-lg ${isPositive ? 'bg-positive/10' : isNegative ? 'bg-negative/10' : 'bg-muted'}`}>
            {isPositive ? <TrendingUp className="h-4 w-4 text-positive" /> :
              isNegative ? <TrendingDown className="h-4 w-4 text-negative" /> :
                <Minus className="h-4 w-4 text-muted-foreground" />}
          </div>
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold tracking-tight ${isPositive ? 'text-positive' : isNegative ? 'text-negative' : ''}`}>
            {daily_return_pct > 0 ? "+" : ""}{(daily_return_pct || 0).toFixed(2)}%
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Chênh lệch mua-bán</CardTitle>
          <div className="p-2 bg-blue-500/10 rounded-lg">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" className="h-4 w-4 text-blue-500">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight">{formatCurrency(spread, metadata.unit)}</div>
          <p className="text-xs text-muted-foreground mt-1 font-medium">Spread</p>
        </CardContent>
      </Card>

      {/* Compare Summary Row */}
      {mode === "compare" && compareData.length > 0 && (
        <div className="col-span-full mt-2 bg-card/30 border border-border/50 rounded-xl p-3 flex flex-wrap gap-4 items-center text-sm backdrop-blur-sm">
          <span className="font-medium text-muted-foreground mr-2">So sánh nhanh:</span>
          {compareData.map(c => {
            const isCPositive = c.daily_return_pct > 0;
            const isCNegative = c.daily_return_pct < 0;
            return (
              <Badge key={c.type_code} variant="outline" className="bg-background/50 flex items-center gap-1.5 py-1 px-2 border-border/50">
                <span className="text-muted-foreground">{c.metadata.market} {c.type_code.replace(c.metadata.market, '')}</span>
                <span className="font-semibold tabular-nums">{formatCurrency(c.buy_price, c.metadata.unit)}</span>
                <span className={`tabular-nums ${isCPositive ? 'text-positive' : isCNegative ? 'text-negative' : 'text-muted-foreground'}`}>
                  {isCPositive ? "+" : ""}{(c.daily_return_pct || 0).toFixed(2)}%
                </span>
              </Badge>
            );
          })}
        </div>
      )}
    </div>
  );
}
