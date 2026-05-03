"use client";

import { useState, useEffect } from "react";
import { KPICards } from "@/components/dashboard/kpi-cards";
import { PriceTrendChart } from "@/components/dashboard/price-trend-chart";
import { TechnicalIndicators } from "@/components/dashboard/technical-indicators";
import { RecentNewsTable } from "@/components/dashboard/recent-news-table";
import { NewsKpiSummary } from "@/components/dashboard/news-kpi-summary";
import { DashboardToolbar, DashboardMode, TimeRange, AVAILABLE_ASSETS } from "@/components/dashboard/dashboard-toolbar";
import { MarketOverviewTable } from "@/components/dashboard/market-overview-table";
import { fetchAPI } from "@/lib/api";
import { LatestPriceResponse, PriceHistoryResponse, LatestNewsResponse, PriceTimeseriesResponse, PriceTimeseriesPoint, NewsSummaryResponse } from "@/lib/types";

export default function DashboardPage() {
  const [mode, setMode] = useState<DashboardMode>("single");
  const [primaryAsset, setPrimaryAsset] = useState<string>("SJL1L10");
  const [compareAssets, setCompareAssets] = useState<string[]>(["SJL1L10", "XAUUSD"]);
  const [timeRange, setTimeRange] = useState<TimeRange>("30D");

  const [latestPrice, setLatestPrice] = useState<LatestPriceResponse | null>(null);
  const [priceHistories, setPriceHistories] = useState<PriceHistoryResponse[]>([]);
  const [timeseries, setTimeseries] = useState<Record<string, PriceTimeseriesPoint[]>>({});
  const [latestNews, setLatestNews] = useState<LatestNewsResponse | null>(null);
  const [newsSummary, setNewsSummary] = useState<NewsSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      const days = timeRange === "7D" ? 7 : timeRange === "30D" ? 30 : timeRange === "90D" ? 90 : 180;

      const targetAssets = mode === "compare"
        ? [primaryAsset, ...compareAssets.filter(a => a !== primaryAsset)]
        : [primaryAsset];

      const historyPromises = targetAssets.map(asset =>
        fetchAPI<PriceHistoryResponse>(`/api/price/history?type=${asset}&days=${days}`)
      );

      const timeseriesPromises = targetAssets.map(asset =>
        fetchAPI<PriceTimeseriesResponse>(`/api/price/timeseries?type=${asset}&days=${days}`)
      );

      const [latestRes, newsRes, summaryRes, ...results] = await Promise.allSettled([
        fetchAPI<LatestPriceResponse>(`/api/price/latest`),
        fetchAPI<LatestNewsResponse>("/api/news/latest?limit=5"),
        fetchAPI<NewsSummaryResponse>(`/api/news/summary?days=7`),
        ...historyPromises,
        ...timeseriesPromises
      ]);

      if (latestRes.status === "fulfilled") setLatestPrice(latestRes.value);
      if (newsRes.status === "fulfilled") setLatestNews(newsRes.value);
      if (summaryRes.status === "fulfilled") setNewsSummary(summaryRes.value);

      const historyResults = results.slice(0, targetAssets.length);
      const timeseriesResults = results.slice(targetAssets.length);

      const validHistories = historyResults
        .filter((r): r is PromiseFulfilledResult<PriceHistoryResponse> => r.status === "fulfilled" && r.value.ok)
        .map(r => r.value);

      const newTimeseries: Record<string, PriceTimeseriesPoint[]> = {};
      timeseriesResults.forEach((r) => {
        if (r.status === "fulfilled" && r.value.ok) {
          const val = r.value as PriceTimeseriesResponse;
          if (val.data) {
            newTimeseries[val.type_code] = val.data;
          }
        }
      });

      setPriceHistories(validHistories);
      setTimeseries(newTimeseries);
      setIsLoading(false);
    }

    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
  }, [primaryAsset, compareAssets, mode, timeRange]);

  const primaryPriceData = latestPrice?.ok
    ? latestPrice.prices.find(p => p.type_code === primaryAsset) || latestPrice.prices[0]
    : null;

  const primaryHistory = priceHistories.find(h => h.type_code === primaryAsset) || priceHistories[0];

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-4 md:pt-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-2 gap-2">
        <div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">Thị trường</h2>
          <p className="text-sm md:text-base text-muted-foreground mt-1">Phân tích chuyên sâu & Toàn cảnh thị trường</p>
        </div>
      </div>

      <DashboardToolbar
        mode={mode}
        setMode={setMode}
        primaryAsset={primaryAsset}
        setPrimaryAsset={setPrimaryAsset}
        compareAssets={compareAssets}
        setCompareAssets={setCompareAssets}
        timeRange={timeRange}
        setTimeRange={setTimeRange}
      />

      <div className="space-y-4">
        {isLoading && !primaryPriceData ? (
          <div className="p-4 border border-border/50 rounded-xl bg-card/50 text-sm text-muted-foreground flex items-center justify-center h-24">
            Đang tải dữ liệu thị trường...
          </div>
        ) : primaryPriceData ? (
          <KPICards
            priceData={{
              ...primaryPriceData,
              // Override with history-calculated values when available
              ...(primaryHistory?.latest && {
                buy_price: primaryHistory.latest.buy_price,
                sell_price: primaryHistory.latest.sell_price,
                mid_price: primaryHistory.latest.mid_price,
                spread: primaryHistory.latest.spread,
              }),
              // Use period change_pct from history instead of DB daily_return_pct
              daily_return_pct: primaryHistory?.change_pct ?? primaryPriceData.daily_return_pct,
            }}
            mode={mode}
            compareData={
              mode === "compare" && latestPrice
                ? latestPrice.prices.filter(p => compareAssets.includes(p.type_code) && p.type_code !== primaryAsset)
                : []
            }
          />
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <div className="col-span-4 h-full">
            {priceHistories.length > 0 ? (
              <PriceTrendChart histories={priceHistories} timeseries={timeseries} mode={mode} />
            ) : (
              <div className="p-4 text-sm text-muted-foreground border border-border/50 rounded-xl bg-card/50 h-[300px] flex items-center justify-center">
                Đang tải biểu đồ giá...
              </div>
            )}
          </div>

          <div className="col-span-3 h-full">
            {primaryHistory ? (
              <TechnicalIndicators
                historyData={primaryHistory}
                mode={mode}
                compareHistories={mode === "compare" ? priceHistories.filter(h => h.type_code !== primaryAsset) : []}
              />
            ) : (
              <div className="p-4 text-sm text-muted-foreground border border-border/50 rounded-xl bg-card/50 h-[300px] flex items-center justify-center">
                Đang tải chỉ báo kỹ thuật...
              </div>
            )}
          </div>
        </div>

        <div className="h-full pt-4">
          {latestPrice?.ok ? (
            <MarketOverviewTable
              latestPrice={latestPrice}
              priceHistories={priceHistories}
              mode={mode}
              primaryAsset={primaryAsset}
              setPrimaryAsset={setPrimaryAsset}
              compareAssets={compareAssets}
              setCompareAssets={setCompareAssets}
            />
          ) : (
            <div className="p-4 text-sm text-muted-foreground border border-border/50 rounded-xl bg-card/50 h-32 flex items-center justify-center">
              Đang tải dữ liệu toàn cảnh thị trường...
            </div>
          )}
        </div>

        <div className="h-full mt-8">
          <div className="mb-4">
            {newsSummary?.ok ? (
              <NewsKpiSummary summary={newsSummary} />
            ) : (
              <div className="p-4 text-sm text-muted-foreground border border-border/50 rounded-xl bg-card/50 h-24 flex items-center justify-center">
                Đang tải thống kê tin tức...
              </div>
            )}
          </div>
          {latestNews?.ok ? (
            <RecentNewsTable newsData={latestNews.articles} />
          ) : (
            <div className="p-4 text-sm text-muted-foreground border border-border/50 rounded-xl bg-card/50 h-32 flex items-center justify-center">
              Đang tải tin tức...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
