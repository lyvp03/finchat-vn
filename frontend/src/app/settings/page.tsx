"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Activity, Database, Moon, Sun, Monitor, RefreshCcw, ExternalLink } from "lucide-react";
import { LatestPriceResponse, LatestNewsResponse } from "@/lib/types";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [healthStatus, setHealthStatus] = useState<string>("checking");
  const [dataFreshness, setDataFreshness] = useState<{
    priceTs: string | null;
    newsTs: string | null;
    isStale: boolean;
  }>({ priceTs: null, newsTs: null, isStale: false });
  const [isChecking, setIsChecking] = useState(false);

  const checkHealth = async () => {
    setIsChecking(true);
    try {
      // Check basic health
      const healthRes = await fetchAPI<Record<string, unknown>>("/api/health");
      setHealthStatus(healthRes.status === "ok" ? "healthy" : "error");

      // Check data freshness
      const [priceRes, newsRes] = await Promise.allSettled([
        fetchAPI<LatestPriceResponse>("/api/price/latest?type=SJL1L10"),
        fetchAPI<LatestNewsResponse>("/api/news/latest?limit=1")
      ]);

      let latestPriceTs = null;
      let latestNewsTs = null;
      let isStale = false;

      if (priceRes.status === "fulfilled" && priceRes.value.ok && priceRes.value.prices.length > 0) {
        latestPriceTs = priceRes.value.prices[0].ts;
      }
      
      if (newsRes.status === "fulfilled" && newsRes.value.ok && newsRes.value.articles.length > 0) {
        latestNewsTs = newsRes.value.articles[0].published_at;
      }

      // If price data is older than 24 hours, consider it stale
      if (latestPriceTs) {
        const priceAge = Date.now() - new Date(latestPriceTs).getTime();
        if (priceAge > 24 * 60 * 60 * 1000) isStale = true;
      }

      setDataFreshness({ priceTs: latestPriceTs, newsTs: latestNewsTs, isStale });

    } catch (err) {
      setHealthStatus("error");
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    checkHealth();
  }, []);

  const formatTimeAgo = (dateString: string | null) => {
    if (!dateString) return "Không có dữ liệu";
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays} ngày trước`;
    if (diffHours > 0) return `${diffHours} giờ trước`;
    if (diffMins > 0) return `${diffMins} phút trước`;
    return "Vừa xong";
  };

  return (
    <div className="p-8 pt-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Cài đặt & giám sát</h2>
        <p className="text-muted-foreground mt-1">
          Quản lý giao diện và theo dõi trạng thái hệ thống
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Appearance Settings */}
        <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
          <CardHeader className="border-b border-border/50 bg-card/50">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Monitor className="h-5 w-5 text-primary" />
              Giao diện
            </CardTitle>
            <CardDescription>Tùy chỉnh chủ đề sáng/tối</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-3 gap-3">
              <Button 
                variant={theme === "light" ? "default" : "outline"}
                className={`w-full justify-start ${theme === "light" ? "bg-primary text-primary-foreground" : "bg-background/50 border-border/50 text-muted-foreground hover:bg-muted"}`}
                onClick={() => setTheme("light")}
              >
                <Sun className="h-4 w-4 mr-2" />
                Sáng
              </Button>
              <Button 
                variant={theme === "dark" ? "default" : "outline"}
                className={`w-full justify-start ${theme === "dark" ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" : "bg-background/50 border-border/50 text-muted-foreground hover:bg-muted"}`}
                onClick={() => setTheme("dark")}
              >
                <Moon className="h-4 w-4 mr-2" />
                Tối
              </Button>
              <Button 
                variant={theme === "system" ? "default" : "outline"}
                className={`w-full justify-start ${theme === "system" ? "bg-primary text-primary-foreground" : "bg-background/50 border-border/50 text-muted-foreground hover:bg-muted"}`}
                onClick={() => setTheme("system")}
              >
                <Monitor className="h-4 w-4 mr-2" />
                Auto
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* System Health */}
        <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-border/50 bg-card/50">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Activity className="h-5 w-5 text-primary" />
                Trạng thái hệ thống
              </CardTitle>
              <CardDescription>API & Database Health</CardDescription>
            </div>
            <Button variant="outline" size="icon" onClick={checkHealth} disabled={isChecking} className="border-border/50 bg-background/50 hover:bg-muted">
              <RefreshCcw className={`h-4 w-4 ${isChecking ? 'animate-spin' : 'text-muted-foreground'}`} />
            </Button>
          </CardHeader>
          <CardContent className="p-6 space-y-5">
            <div className="flex items-center justify-between p-3 rounded-lg bg-background/50 border border-border/50">
              <span className="text-sm font-medium text-foreground">Backend API (Render)</span>
              {healthStatus === "checking" ? (
                <Badge variant="outline" className="text-muted-foreground bg-muted/50 border-border/50">Đang kiểm tra...</Badge>
              ) : healthStatus === "healthy" ? (
                <Badge variant="outline" className="bg-positive/10 text-positive border-positive/20 flex items-center gap-1.5 shadow-[0_0_10px_rgba(16,185,129,0.1)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-positive animate-pulse" />
                  Online
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-negative/10 text-negative border-negative/20 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-negative" />
                  Offline
                </Badge>
              )}
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <Database className="h-4 w-4" />
                  Cập nhật giá
                </div>
                <span className="text-sm font-semibold tabular-nums text-foreground">
                  {formatTimeAgo(dataFreshness.priceTs)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <Database className="h-4 w-4" />
                  Cập nhật tin tức
                </div>
                <span className="text-sm font-semibold tabular-nums text-foreground">
                  {formatTimeAgo(dataFreshness.newsTs)}
                </span>
              </div>
            </div>

            {dataFreshness.isStale && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-start gap-2">
                <span className="text-destructive text-lg leading-none mt-0.5">⚠️</span>
                <p className="text-xs text-destructive font-medium leading-relaxed">
                  Cảnh báo: Dữ liệu có thể đã cũ do crawler chưa được chạy hoặc gặp lỗi.
                </p>
              </div>
            )}
            
            <div className="pt-4 border-t border-border/50">
              <a 
                href="https://github.com/lyvp03/finchat-vn/actions" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center justify-between group p-3 rounded-lg hover:bg-background/50 border border-transparent hover:border-border/50 transition-all"
              >
                <div className="text-sm font-medium group-hover:text-primary transition-colors">
                  GitHub Actions Crawler
                </div>
                <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </a>
              <p className="text-xs text-muted-foreground mt-2 px-3">
                Kiểm tra log của các cron job crawl dữ liệu trên Github.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
