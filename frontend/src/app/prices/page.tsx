"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";
import { LatestPriceResponse, PriceData, PriceHistoryResponse, PriceTimeseriesResponse, PriceTimeseriesPoint } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownRight, RefreshCcw, Minus, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PriceTrendChart } from "@/components/dashboard/price-trend-chart";
import { AVAILABLE_ASSETS } from "@/components/dashboard/dashboard-toolbar";

export default function PricesPage() {
  const [data, setData] = useState<PriceData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedAsset, setSelectedAsset] = useState<string>("SJL1L10");
  const [history, setHistory] = useState<PriceHistoryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<Record<string, PriceTimeseriesPoint[]>>({});

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchAPI<LatestPriceResponse>("/api/price/latest");
      if (res.ok) {
        setData(res.prices);
      } else {
        setError("Không lấy được dữ liệu từ server");
      }
    } catch (err) {
      setError("Lỗi kết nối đến server");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, []);

  useEffect(() => {
    async function loadChartData() {
      try {
        const [histRes, tsRes] = await Promise.all([
          fetchAPI<PriceHistoryResponse>(`/api/price/history?type=${selectedAsset}&days=30`),
          fetchAPI<PriceTimeseriesResponse>(`/api/price/timeseries?type=${selectedAsset}&days=30`)
        ]);
        if (histRes.ok) setHistory(histRes);
        if (tsRes.ok && tsRes.data) {
          setTimeseries({ [selectedAsset]: tsRes.data });
        }
      } catch (e) {
        console.error("Failed to load chart data:", e);
      }
    }
    loadChartData();
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
        <Button variant="outline" onClick={loadData} disabled={isLoading} className="border-border/50 hover:bg-muted/50">
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
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                    <div className="flex justify-center items-center gap-2">
                      <RefreshCcw className="h-4 w-4 animate-spin" /> Đang tải dữ liệu...
                    </div>
                  </TableCell>
                </TableRow>
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
            <div className="h-full border border-border/50 rounded-xl bg-card/50 flex items-center justify-center text-muted-foreground">
              Đang tải biểu đồ...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
