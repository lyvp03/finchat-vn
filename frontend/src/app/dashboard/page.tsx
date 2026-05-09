"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { KPICards } from "@/components/dashboard/kpi-cards";
import { TechnicalIndicators } from "@/components/dashboard/technical-indicators";
import { RecentNewsTable } from "@/components/dashboard/recent-news-table";
import { NewsKpiSummary } from "@/components/dashboard/news-kpi-summary";
import { DashboardToolbar, DashboardMode, TimeRange, AVAILABLE_ASSETS } from "@/components/dashboard/dashboard-toolbar";
import { MarketOverviewTable } from "@/components/dashboard/market-overview-table";
import {
  KPICardsSkeleton,
  ChartSkeleton,
  TechnicalIndicatorsSkeleton,
  MarketOverviewSkeleton,
  NewsKpiSkeleton,
  NewsTableSkeleton,
} from "@/components/dashboard/skeletons";
import { fetchAPI, fetchWithSWR } from "@/lib/api";
import { LatestPriceResponse, PriceHistoryResponse, LatestNewsResponse, PriceTimeseriesResponse, PriceTimeseriesPoint, NewsSummaryResponse } from "@/lib/types";
import { useRef } from "react";

// Lazy-load the heavy recharts-based component
const PriceTrendChart = dynamic(
  () => import("@/components/dashboard/price-trend-chart").then(mod => ({ default: mod.PriceTrendChart })),
  { ssr: false, loading: () => <ChartSkeleton /> }
);

export default function DashboardPage() {
  const [mode, setMode] = useState<DashboardMode>("single");
  const [primaryAsset, setPrimaryAsset] = useState<string>("SJL1L10");
  const [compareAssets, setCompareAssets] = useState<string[]>(["SJL1L10", "XAUUSD"]);
  const [timeRange, setTimeRange] = useState<TimeRange>("30D");

  // Each section has independent loading state
  const [latestPrice, setLatestPrice] = useState<LatestPriceResponse | null>(null);
  const [priceHistories, setPriceHistories] = useState<PriceHistoryResponse[]>([]);
  const [timeseries, setTimeseries] = useState<Record<string, PriceTimeseriesPoint[]>>({});
  const [latestNews, setLatestNews] = useState<LatestNewsResponse | null>(null);
  const [newsSummary, setNewsSummary] = useState<NewsSummaryResponse | null>(null);

  const [loadingPrices, setLoadingPrices] = useState(true);
  const [loadingHistories, setLoadingHistories] = useState(true);
  const [loadingNews, setLoadingNews] = useState(true);
  const [loadingNewsSummary, setLoadingNewsSummary] = useState(true);

  const abortControllerRef = useRef<AbortController | null>(null);
  const seqIdRef = useRef(0);

  const loadData = useCallback(async () => {
    // Cancel previous request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const currentSeq = ++seqIdRef.current;

    const days = timeRange === "7D" ? 7 : timeRange === "30D" ? 30 : timeRange === "90D" ? 90 : 180;
    const targetAssets = mode === "compare"
      ? [primaryAsset, ...compareAssets.filter(a => a !== primaryAsset)]
      : [primaryAsset];

    // Reset loading states
    setLoadingPrices(true);
    setLoadingHistories(true);
    setLoadingNews(true);
    setLoadingNewsSummary(true);

    // === PROGRESSIVE LOADING: Each section loads independently ===

    // 1. Latest Prices — fastest endpoint, show KPI cards ASAP
    fetchWithSWR<LatestPriceResponse>(`/api/price/latest`, { ttlMs: 15000, signal: controller.signal })
      .then(({ data }) => {
        if (currentSeq === seqIdRef.current && data.ok) {
          setLatestPrice(data);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (currentSeq === seqIdRef.current) setLoadingPrices(false);
      });

    // 2. Price histories + timeseries — for chart & technical indicators
    Promise.all([
      ...targetAssets.map(asset =>
        fetchWithSWR<PriceHistoryResponse>(`/api/price/history?type=${asset}&days=${days}`, { ttlMs: 60000, signal: controller.signal })
          .then(r => ({ type: "history" as const, asset, data: r.data }))
          .catch(() => null)
      ),
      ...targetAssets.map(asset =>
        fetchWithSWR<PriceTimeseriesResponse>(`/api/price/timeseries?type=${asset}&days=${days}`, { ttlMs: 60000, signal: controller.signal })
          .then(r => ({ type: "timeseries" as const, asset, data: r.data }))
          .catch(() => null)
      ),
    ]).then(results => {
      if (currentSeq !== seqIdRef.current) return;

      const validHistories: PriceHistoryResponse[] = [];
      const newTimeseries: Record<string, PriceTimeseriesPoint[]> = {};

      for (const r of results) {
        if (!r) continue;
        if (r.type === "history" && r.data.ok) {
          validHistories.push(r.data);
        }
        if (r.type === "timeseries" && r.data.ok && (r.data as PriceTimeseriesResponse).data) {
          newTimeseries[(r.data as PriceTimeseriesResponse).type_code] = (r.data as PriceTimeseriesResponse).data;
        }
      }

      setPriceHistories(validHistories);
      setTimeseries(newTimeseries);
    }).finally(() => {
      if (currentSeq === seqIdRef.current) setLoadingHistories(false);
    });

    // 3. News — independent
    fetchWithSWR<LatestNewsResponse>("/api/news/latest?limit=5", { ttlMs: 60000, signal: controller.signal })
      .then(({ data }) => {
        if (currentSeq === seqIdRef.current && data.ok) {
          setLatestNews(data);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (currentSeq === seqIdRef.current) setLoadingNews(false);
      });

    // 4. News summary — independent
    fetchWithSWR<NewsSummaryResponse>(`/api/news/summary?days=7`, { ttlMs: 60000, signal: controller.signal })
      .then(({ data }) => {
        if (currentSeq === seqIdRef.current && data.ok) {
          setNewsSummary(data);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (currentSeq === seqIdRef.current) setLoadingNewsSummary(false);
      });
  }, [primaryAsset, compareAssets, mode, timeRange]);

  useEffect(() => {
    loadData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadData]);


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
        {/* KPI Cards — loads first */}
        {primaryPriceData ? (
          <KPICards
            priceData={{
              ...primaryPriceData,
              ...(primaryHistory?.latest && {
                buy_price: primaryHistory.latest.buy_price,
                sell_price: primaryHistory.latest.sell_price,
                mid_price: primaryHistory.latest.mid_price,
                spread: primaryHistory.latest.spread,
              }),
              daily_return_pct: primaryHistory?.change_pct ?? primaryPriceData.daily_return_pct,
            }}
            mode={mode}
            compareData={
              mode === "compare" && latestPrice
                ? latestPrice.prices.filter(p => compareAssets.includes(p.type_code) && p.type_code !== primaryAsset)
                : []
            }
          />
        ) : loadingPrices ? (
          <KPICardsSkeleton />
        ) : null}

        {/* Chart + Technical Indicators */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <div className="col-span-4 h-full">
            {priceHistories.length > 0 ? (
              <PriceTrendChart histories={priceHistories} timeseries={timeseries} mode={mode} />
            ) : loadingHistories ? (
              <ChartSkeleton />
            ) : (
              <div className="p-4 text-sm text-muted-foreground border border-border/50 rounded-xl bg-card/50 h-[300px] flex items-center justify-center">
                Không có dữ liệu biểu đồ
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
            ) : loadingHistories ? (
              <TechnicalIndicatorsSkeleton />
            ) : (
              <div className="p-4 text-sm text-muted-foreground border border-border/50 rounded-xl bg-card/50 h-[300px] flex items-center justify-center">
                Không có dữ liệu chỉ báo
              </div>
            )}
          </div>
        </div>

        {/* Market Overview Table */}
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
          ) : loadingPrices ? (
            <MarketOverviewSkeleton />
          ) : null}
        </div>

        {/* News Section */}
        <div className="h-full mt-8">
          <div className="mb-4">
            {newsSummary?.ok ? (
              <NewsKpiSummary summary={newsSummary} />
            ) : loadingNewsSummary ? (
              <NewsKpiSkeleton />
            ) : null}
          </div>
          {latestNews?.ok ? (
            <RecentNewsTable newsData={latestNews.articles} />
          ) : loadingNews ? (
            <NewsTableSkeleton />
          ) : null}
        </div>
      </div>
    </div>
  );
}
