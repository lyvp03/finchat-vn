"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { fetchAPI, fetchWithSWR } from "@/lib/api";
import { LatestPriceResponse, PriceData, PriceHistoryResponse, PriceTimeseriesResponse, PriceTimeseriesPoint } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownRight, RefreshCcw, Minus, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChartSkeleton } from "@/components/dashboard/skeletons";
import { AVAILABLE_ASSETS } from "@/components/dashboard/dashboard-toolbar";
import { useRef } from "react";

// Lazy-load chart component
const PriceTrendChart = dynamic(
  () => import("@/components/dashboard/price-trend-chart").then(mod => ({ default: mod.PriceTrendChart })),
  { ssr: false, loading: () => <ChartSkeleton /> }
);

export default function PricesPage() {
  const [data, setData] = useState<PriceData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedAsset, setSelectedAsset] = useState<string>("SJL1L10");
  const [history, setHistory] = useState<PriceHistoryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<Record<string, PriceTimeseriesPoint[]>>({});

  const abortLatestRef = useRef<AbortController | null>(null);
  const abortChartRef = useRef<AbortController | null>(null);
  const chartSeqIdRef = useRef(0);

  const loadData = useCallback(async (forceRefresh = false) => {
    if (abortLatestRef.current) {
      abortLatestRef.current.abort();
    }
    const controller = new AbortController();
    abortLatestRef.current = controller;

    setIsLoading(true);
    setError(null);
    try {
      const endpoint = "/api/price/latest";

      if (forceRefresh) {
        // Force fresh fetch
        const res = await fetchAPI<LatestPriceResponse>(endpoint, { signal: controller.signal });
        if (res.ok) {
          setData(res.prices);
          // Update sessionStorage cache
          try {
            sessionStorage.setItem(`swr:${endpoint}`, JSON.stringify({
              data: res,
              expiry: Date.now() + 15000,
            }));
          } catch {}
        } else {
          setError("Không lấy được dữ liệu từ server");
        }
      } else {
        const { data: res } = await fetchWithSWR<LatestPriceResponse>(endpoint, {
          ttlMs: 15000,
          signal: controller.signal,
        });
        if (res.ok) {
          setData(res.prices);
        } else {
          setError("Không lấy được dữ liệu từ server");
        }
      }
    } catch (err: any) {
      if (err.status === 408 || err.name === "AbortError") return;
      setError("Lỗi kết nối đến server");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    return () => {
      if (abortLatestRef.current) abortLatestRef.current.abort();
    };
  }, [loadData]);

  useEffect(() => {
    async function loadChartData() {
      if (abortChartRef.current) {
        abortChartRef.current.abort();
      }
      const controller = new AbortController();
      abortChartRef.current = controller;
      const currentSeq = ++chartSeqIdRef.current;

      try {
        const [histResult, tsResult] = await Promise.all([
          fetchWithSWR<PriceHistoryResponse>(`/api/price/history?type=${selectedAsset}&days=30`, {
            ttlMs: 60000,
            signal: controller.signal,
          }),
          fetchWithSWR<PriceTimeseriesResponse>(`/api/price/timeseries?type=${selectedAsset}&days=30`, {
            ttlMs: 60000,
            signal: controller.signal,
          }),
        ]);

        if (currentSeq !== chartSeqIdRef.current) return;

        if (histResult.data.ok) setHistory(histResult.data);
        if (tsResult.data.ok && (tsResult.data as PriceTimeseriesResponse).data) {
          setTimeseries({ [selectedAsset]: (tsResult.data as PriceTimeseriesResponse).data });
        }
      } catch (e: any) {
        if (e.status === 408 || e.name === "AbortError") return;
        console.error("Failed to load chart data:", e);
      }
    }
    loadChartData();
    
    return () => {
      if (abortChartRef.current) abortChartRef.current.abort();
    };
  }, [selectedAsset]);

  const formatCurrency = (val: number, unit: string) => {
    const formatted = new Intl.NumberFormat('vi-VN').format(val);
    return `${formatted} ${unit === 'USD/oz' ? 'USD' : 'VND'}`;
  };

  return (
    <div className="p-8 pt-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Giá vàng thời gian thực</h2>
          <p className="text-muted-foreground mt-1">Cập nhật giá mua, bán và chênh lệch các loại vàng</p>
        </div>
        <Button variant="outline" onClick={() => loadData(true)} disabled={isLoading} className="border-border/50 hover:bg-muted/50">
          <RefreshCcw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Làm mới
        </Button>
      </div>

      <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm overflow-hidden">
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-background/50 border-b border-border/50">
              <TableRow className="hover:bg-transparent border-border/50">
                <TableHead className="text-foreground font-semibold text-sm">Loại vàng</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Mua vào</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Bán ra</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Chênh lệch</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Biến động</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Cập nhật</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading && data.length === 0 ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i} className="border-border/50">
                    <TableCell>
                      <div className="space-y-2">
                        <div className="h-5 w-36 bg-muted animate-pulse rounded" style={{ animationDelay: `${i * 80}ms` }} />
                        <div className="h-4 w-24 bg-muted/60 animate-pulse rounded" />
                      </div>
                    </TableCell>
                    <TableCell className="text-right"><div className="h-5 w-28 bg-muted animate-pulse rounded ml-auto" /></TableCell>
                    <TableCell className="text-right"><div className="h-5 w-28 bg-muted animate-pulse rounded ml-auto" /></TableCell>
                    <TableCell className="text-right"><div className="h-5 w-20 bg-muted animate-pulse rounded ml-auto" /></TableCell>
                    <TableCell className="text-right"><div className="h-5 w-16 bg-muted animate-pulse rounded ml-auto" /></TableCell>
                    <TableCell className="text-right"><div className="h-4 w-16 bg-muted animate-pulse rounded ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-destructive">
                    {error}
                  </TableCell>
                </TableRow>
              ) : (
                data.map((item) => {
                  const isPositive = item.daily_return_pct > 0;
                  const isNegative = item.daily_return_pct < 0;
                  
                  return (
                    <TableRow 
                      key={item.type_code} 
                      className={`border-border/50 hover:bg-muted/50 transition-colors cursor-pointer ${selectedAsset === item.type_code ? 'bg-primary/5' : ''}`}
                      onClick={() => setSelectedAsset(item.type_code)}
                    >
                      <TableCell>
                        <div className="font-semibold text-base text-foreground flex items-center gap-2">
                          {AVAILABLE_ASSETS.find(a => a.id === item.type_code)?.name || item.metadata.name}
                          {selectedAsset === item.type_code && <TrendingUp className="h-4 w-4 text-primary" />}
                        </div>
                        <div className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs h-5 px-2 font-medium capitalize border-border/50">
                            {item.metadata.market}
                          </Badge>
                          <span className="uppercase font-medium">{item.type_code}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-base font-semibold tabular-nums text-foreground">
                        {formatCurrency(item.buy_price, item.metadata.unit)}
                      </TableCell>
                      <TableCell className="text-right text-base font-semibold tabular-nums text-foreground">
                        {formatCurrency(item.sell_price, item.metadata.unit)}
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground tabular-nums text-sm font-medium">
                        {new Intl.NumberFormat('vi-VN').format(item.spread)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-base">
                        <div className={`flex items-center justify-end gap-1 font-semibold ${
                          isPositive ? 'text-positive' : isNegative ? 'text-negative' : 'text-muted-foreground'
                        }`}>
                          {isPositive ? <ArrowUpRight className="h-4 w-4" /> : 
                           isNegative ? <ArrowDownRight className="h-4 w-4" /> : <Minus className="h-4 w-4" />}
                          {isPositive ? "+" : ""}{item.daily_return_pct.toFixed(2)}%
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground tabular-nums">
                        {new Date(item.ts).toLocaleTimeString("vi-VN", { hour: '2-digit', minute: '2-digit' })}
                        <br/>
                        {new Date(item.ts).toLocaleDateString("vi-VN", { month: 'short', day: 'numeric' })}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      
      <div className="mt-8">
        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" /> 
          Biểu đồ giá 30 ngày ({AVAILABLE_ASSETS.find(a => a.id === selectedAsset)?.name || data.find(d => d.type_code === selectedAsset)?.metadata.name || selectedAsset})
        </h3>
        <div className="h-[400px]">
          {history ? (
            <PriceTrendChart histories={[history]} timeseries={timeseries} mode="single" />
          ) : (
            <ChartSkeleton />
          )}
        </div>
      </div>
    </div>
  );
}
