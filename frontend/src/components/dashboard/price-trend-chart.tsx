"use client";

import { useMemo, useState } from "react";
import { Area, Line, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PriceHistoryResponse, PriceTimeseriesPoint } from "@/lib/types";
import { DashboardMode, AVAILABLE_ASSETS } from "./dashboard-toolbar";
import { Badge } from "@/components/ui/badge";

interface PriceTrendChartProps {
  histories: PriceHistoryResponse[];
  timeseries?: Record<string, PriceTimeseriesPoint[]>;
  mode?: DashboardMode;
}

const CHART_COLORS = [
  "var(--primary)", // Gold
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#a855f7", // Purple
];

export function PriceTrendChart({ histories, timeseries, mode = "single" }: PriceTrendChartProps) {
  const [forcePercentMode] = useState(false);

  const isMixedUnits = useMemo(() => {
    if (histories.length <= 1) return false;
    const firstUnit = histories[0].metadata.unit;
    return histories.some(h => h.metadata.unit !== firstUnit);
  }, [histories]);

  const usePercentMode = mode === "compare" && (isMixedUnits || forcePercentMode);

  const chartData = useMemo(() => {
    if (timeseries && Object.keys(timeseries).length > 0) {
      const dataMap: Record<string, any> = {};
      
      Object.entries(timeseries).forEach(([typeCode, points]) => {
        if (!points) return;
        points.forEach(point => {
          const dateObj = new Date(point.ts);
          const dateStr = dateObj.toLocaleDateString("vi-VN", { month: "short", day: "numeric" });
          const key = dateStr; // Group by day for the chart x-axis to look clean
          
          if (!dataMap[key]) {
              dataMap[key] = {
                  date: dateStr,
                  fullDate: dateObj,
              };
          }
          
          const absolutePrice = point.mid_price;
          if (usePercentMode) {
              const firstPoint = points[0];
              const startPrice = firstPoint ? firstPoint.mid_price : absolutePrice;
              dataMap[key][`val_${typeCode}`] = startPrice ? ((absolutePrice / startPrice) - 1) * 100 : 0;
          } else {
              dataMap[key][`val_${typeCode}`] = absolutePrice;
          }
        });
      });
      return Object.values(dataMap).sort((a: any, b: any) => a.fullDate.getTime() - b.fullDate.getTime());
    }

    // Fallback to interpolated data if timeseries is not yet available
    if (!histories.length) return [];

    const maxDays = Math.max(...histories.map(h => h.period_days));
    const data = [];

    for (let i = 0; i <= maxDays; i++) {
      const dataPoint: Record<string, number | string | Date> = {};

      const date = new Date(histories[0].from);
      date.setDate(date.getDate() + i);
      dataPoint.date = date.toLocaleDateString("vi-VN", { month: "short", day: "numeric" });
      dataPoint.fullDate = date;

      histories.forEach(h => {
        if (i > h.period_days) return;

        const progress = i / h.period_days;
        const startPrice = h.start_mid_price;
        const endPrice = h.latest.mid_price;
        const basePrice = startPrice + (endPrice - startPrice) * progress;

        const seed = (h.type_code.charCodeAt(0) + i) % 100;
        const noiseFactor = h.metadata.unit === "USD/oz" ? 10 : 500000;
        const noise = ((seed / 100) - 0.5) * noiseFactor;

        const absolutePrice = i === 0 ? startPrice : i === h.period_days ? endPrice : basePrice + noise;

        if (usePercentMode) {
          dataPoint[`val_${h.type_code}`] = ((absolutePrice / startPrice) - 1) * 100;
        } else {
          dataPoint[`val_${h.type_code}`] = absolutePrice;
        }
      });

      data.push(dataPoint);
    }
    return data;
  }, [histories, timeseries, usePercentMode]);

  const formatYAxis = (val: number) => {
    if (usePercentMode) return `${val > 0 ? '+' : ''}${val.toFixed(1)}%`;
    if (val > 1000000) return `${(val / 1000000).toFixed(0)}tr`;
    return val.toLocaleString();
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const formatTooltip = (val: any, name: any) => {
    const nameStr = String(name);
    const key = nameStr.replace('val_', '');
    const asset = histories.find(h => h.type_code === key);
    const label = asset ? `${asset.metadata.market} ${asset.type_code.replace(asset.metadata.market, '')}` : nameStr;

    const numericVal = Number(val);
    if (usePercentMode) {
      return [`${numericVal > 0 ? '+' : ''}${numericVal.toFixed(2)}%`, label];
    }

    const formattedVal = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: asset?.metadata.unit === 'USD/oz' ? 'USD' : 'VND' }).format(numericVal);
    return [formattedVal, label];
  };

  return (
    <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm h-full flex flex-col relative overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500"><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" /></svg>
              Xu hướng giá {mode === "compare" && "so sánh"}
            </CardTitle>
            <CardDescription className="mt-1">
              {mode === "single"
                ? `Biến động giá vàng ${AVAILABLE_ASSETS.find(a => a.id === histories[0]?.type_code)?.name || histories[0]?.metadata.name} trong ${histories[0]?.period_days} ngày qua`
                : "So sánh biến động giữa các tài sản"}
            </CardDescription>
          </div>
          {mode === "compare" && (
            <div className="flex gap-2">
              <Badge variant="outline" className="border-border/50 text-xs font-normal">
                {isMixedUnits ? "Tự động chuẩn hóa %" : "Tuyệt đối"}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 min-h-[300px] pt-4">
        {mode === "compare" && isMixedUnits && (
          <div className="mb-4 text-xs text-muted-foreground bg-muted/30 p-2 rounded border border-border/50 border-dashed text-center">
            ⚠️ Phát hiện khác biệt đơn vị (VND vs USD). Biểu đồ tự động chuyển sang chế độ % Biến Động (Normalized % Change).
          </div>
        )}
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                {histories.map((h, i) => (
                  <linearGradient key={`grad_${h.type_code}`} id={`color_${h.type_code}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={mode === "single" ? 0.3 : 0.1} />
                    <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" opacity={0.4} />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
                minTickGap={30}
                dy={10}
              />
              <YAxis
                tickFormatter={formatYAxis}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
                domain={['auto', 'auto']}
                width={50}
                dx={-10}
              />
              <Tooltip
                formatter={formatTooltip}
                contentStyle={{ backgroundColor: "var(--color-card)", borderColor: "var(--color-border)", borderRadius: "8px", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                itemStyle={{ fontSize: "13px", fontWeight: 500 }}
                labelStyle={{ fontSize: "12px", color: "var(--color-muted-foreground)", marginBottom: "4px" }}
              />
              {mode === "compare" ? (
                <Legend iconType="circle" wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} formatter={(value) => value.replace('val_', '')} />
              ) : null}

              {histories.map((h, i) => {
                const dataKey = `val_${h.type_code}`;
                const color = CHART_COLORS[i % CHART_COLORS.length];

                if (mode === "single") {
                  return (
                    <Area
                      key={dataKey}
                      type="monotone"
                      dataKey={dataKey}
                      name={dataKey}
                      stroke={color}
                      strokeWidth={2}
                      fillOpacity={1}
                      fill={`url(#color_${h.type_code})`}
                    />
                  );
                } else {
                  return (
                    <Line
                      key={dataKey}
                      type="monotone"
                      dataKey={dataKey}
                      name={dataKey}
                      stroke={color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, strokeWidth: 0 }}
                    />
                  );
                }
              })}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
