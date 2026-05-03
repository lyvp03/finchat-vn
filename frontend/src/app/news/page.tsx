"use client";

import { useState, useEffect } from "react";
import { fetchAPI } from "@/lib/api";
import { LatestNewsResponse, NewsArticle } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ArrowUpRight, ArrowDownRight, Minus, Search, Loader2, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";

export default function NewsPage() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [scope, setScope] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  const loadNews = async (searchQuery = "", marketScope = "all") => {
    setIsLoading(true);
    try {
      let endpoint = "";
      if (searchQuery.trim()) {
        endpoint = `/api/news/search?q=${encodeURIComponent(searchQuery)}&top_k=20`;
        if (marketScope !== "all") endpoint += `&market_scope=${marketScope}`;
      } else {
        endpoint = `/api/news/latest-extended?limit=20`;
        if (marketScope !== "all") endpoint += `&market_scope=${marketScope}`;
      }
      
      const res = await fetchAPI<LatestNewsResponse>(endpoint);
      if (res.ok && res.articles) {
        setArticles(res.articles);
        setCurrentPage(1);
      }
    } catch (err) {
      console.error("Failed to load news:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Debounce search
    const timer = setTimeout(() => {
      loadNews(query, scope);
    }, 500);
    return () => clearTimeout(timer);
  }, [query, scope]);

  const getSentimentIcon = (score: number) => {
    if (score > 0.1) return <ArrowUpRight className="h-4 w-4" />;
    if (score < -0.1) return <ArrowDownRight className="h-4 w-4" />;
    return <Minus className="h-4 w-4" />;
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.1) return "text-emerald-500 bg-emerald-500/10 border-emerald-500/20";
    if (score < -0.1) return "text-red-500 bg-red-500/10 border-red-500/20";
    return "text-muted-foreground bg-muted border-muted-foreground/20";
  };

  return (
    <div className="p-8 pt-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Tin tức thị trường</h2>
        <p className="text-muted-foreground mt-1">
          Dữ liệu tin tức đã được phân tích bằng AI (FinBERT & XLM-Roberta)
        </p>
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-4 bg-card/50 p-4 rounded-xl border border-border/50 backdrop-blur-sm">
        <div className="relative flex-1 w-full group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
          <Input 
            placeholder="Tìm kiếm semantic search (vd: lạm phát tăng)..." 
            className="pl-9 bg-background/50 border-border/50 focus-visible:ring-primary/50 transition-all h-10 shadow-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <Tabs value={scope} onValueChange={setScope} className="w-full sm:w-auto">
          <TabsList className="grid w-full grid-cols-3 sm:w-[320px] h-10 bg-background/50 border border-border/50 p-1 shadow-sm">
            <TabsTrigger value="all" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary transition-all">Tất cả</TabsTrigger>
            <TabsTrigger value="domestic" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary transition-all">Trong nước</TabsTrigger>
            <TabsTrigger value="international" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary transition-all">Thế giới</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {isLoading && articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-16 text-muted-foreground bg-card/30 rounded-xl border border-border/50 border-dashed">
          <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
          <p>Đang truy xuất dữ liệu tin tức...</p>
        </div>
      ) : articles.length === 0 ? (
        <div className="text-center p-16 bg-card/30 rounded-xl border border-border/50 border-dashed">
          <p className="text-muted-foreground font-medium">Không tìm thấy tin tức nào phù hợp.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {articles.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map((article, idx) => (
            <Card key={`${article.id}-${idx}`} className="overflow-hidden border-border/50 bg-gradient-to-r from-card to-card/50 shadow-sm hover:shadow-md transition-shadow group">
              <CardContent className="p-0 flex flex-col sm:flex-row">
                <div className="p-5 flex-1 space-y-4">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="text-xs px-2 uppercase bg-background border-border/50 text-muted-foreground font-medium">
                      {article.source_name}
                    </Badge>
                    <Badge variant="secondary" className="text-xs px-2 font-normal bg-secondary/50 text-secondary-foreground border border-border/50">
                      {article.event_type.replace(/_/g, " ")}
                    </Badge>
                    <span className="text-sm text-muted-foreground ml-auto tabular-nums font-medium">
                      {new Date(article.published_at).toLocaleString("vi-VN", {
                        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
                      })}
                    </span>
                  </div>
                  
                  <div>
                    <Link href={`/news/${article.id}`}>
                      <h3 className="text-xl font-semibold leading-tight mb-2 group-hover:text-primary transition-colors hover:underline">
                        {article.title}
                      </h3>
                    </Link>
                    <p className="text-base text-muted-foreground line-clamp-2 leading-relaxed">
                      {article.summary}
                    </p>
                  </div>
                </div>
                
                <div className="bg-background/40 sm:w-64 border-t sm:border-t-0 sm:border-l border-border/50 p-5 flex flex-row sm:flex-col items-center sm:items-start justify-center gap-6 sm:gap-4 backdrop-blur-sm">
                  <div className="w-full">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Mức độ ảnh hưởng</span>
                      <span className="text-sm font-bold tabular-nums">{(article.impact_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-muted overflow-hidden rounded-full">
                      <div 
                        className="h-full bg-gradient-to-r from-primary/50 to-primary" 
                        style={{ width: `${article.impact_score * 100}%` }}
                      />
                    </div>
                  </div>
                  
                  <div className="w-full sm:mt-auto">
                    <div className="text-sm font-medium text-muted-foreground mb-2 uppercase tracking-wider">Tín hiệu AI</div>
                    <Badge variant="outline" className={`w-full justify-center py-1.5 flex items-center gap-1.5 border text-sm ${getSentimentColor(article.sentiment_score)}`}>
                      {getSentimentIcon(article.sentiment_score)}
                      {article.sentiment_score > 0.1 ? "Tích cực (Bullish)" : 
                       article.sentiment_score < -0.1 ? "Tiêu cực (Bearish)" : "Trung lập (Neutral)"}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Pagination Controls */}
          {articles.length > ITEMS_PER_PAGE && (
            <div className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-border/50">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="w-28 border-border/50 bg-background/50 hover:bg-muted"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Trang trước
              </Button>
              <div className="text-sm font-medium tabular-nums text-muted-foreground">
                Trang {currentPage} / {Math.ceil(articles.length / ITEMS_PER_PAGE)}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.min(Math.ceil(articles.length / ITEMS_PER_PAGE), p + 1))}
                disabled={currentPage >= Math.ceil(articles.length / ITEMS_PER_PAGE)}
                className="w-28 border-border/50 bg-background/50 hover:bg-muted"
              >
                Trang sau
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
