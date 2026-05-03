"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchAPI } from "@/lib/api";
import { NewsDetailResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownRight, Minus, ArrowLeft, ExternalLink, Calendar, Loader2 } from "lucide-react";
import Link from "next/link";

export default function NewsDetailPage() {
  const params = useParams();
  const [data, setData] = useState<NewsDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDetail() {
      if (!params.id) return;
      setIsLoading(true);
      try {
        const res = await fetchAPI<NewsDetailResponse>(`/api/news/${params.id}`);
        if (res.ok) {
          setData(res);
        } else {
          setError("Không tìm thấy bài viết");
        }
      } catch (err) {
        setError("Lỗi kết nối");
      } finally {
        setIsLoading(false);
      }
    }
    loadDetail();
  }, [params.id]);

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

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin mb-4 text-primary" />
        <p>Đang tải bài viết...</p>
      </div>
    );
  }

  if (error || !data?.article) {
    return (
      <div className="p-8 max-w-4xl mx-auto text-center">
        <h2 className="text-2xl font-bold mb-4">{error || "Bài viết không tồn tại"}</h2>
        <Link href="/news">
          <Button variant="outline"><ArrowLeft className="h-4 w-4 mr-2" /> Quay lại danh sách tin tức</Button>
        </Link>
      </div>
    );
  }

  const { article } = data;

  return (
    <div className="p-8 pt-6 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors w-fit">
        <Link href="/news" className="flex items-center gap-2">
          <ArrowLeft className="h-4 w-4" /> Quay lại tin tức
        </Link>
      </div>

      <article className="space-y-6">
        <div className="space-y-4 border-b border-border/50 pb-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-xs px-2 uppercase bg-background border-border/50 font-medium">
              {article.source_name}
            </Badge>
            <Badge variant="secondary" className="text-xs px-2 font-normal bg-secondary/50">
              {article.event_type.replace(/_/g, " ")}
            </Badge>
            {article.news_tier && (
              <Badge variant="outline" className="text-xs px-2 bg-primary/10 text-primary border-primary/20">
                {article.news_tier}
              </Badge>
            )}
            <div className="flex items-center gap-1 text-sm text-muted-foreground ml-auto">
              <Calendar className="h-4 w-4" />
              {new Date(article.published_at).toLocaleString("vi-VN", {
                day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
              })}
            </div>
          </div>

          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-tight text-foreground">
            {article.title}
          </h1>

          <div className="flex flex-wrap gap-4 py-2">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm font-medium ${getSentimentColor(article.sentiment_score)}`}>
              {getSentimentIcon(article.sentiment_score)}
              {article.sentiment_score > 0.1 ? "Tích cực (Bullish)" : 
               article.sentiment_score < -0.1 ? "Tiêu cực (Bearish)" : "Trung lập (Neutral)"}
            </div>
            
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50 border border-border/50 text-sm">
              <span className="text-muted-foreground font-medium">Impact:</span>
              <span className="font-bold">{(article.impact_score * 100).toFixed(0)}%</span>
            </div>
          </div>

          <p className="text-lg text-muted-foreground italic border-l-4 border-primary/50 pl-4 py-1">
            {article.summary}
          </p>
        </div>

        <div className="prose prose-neutral dark:prose-invert max-w-none prose-p:leading-relaxed prose-p:text-[1.05rem] whitespace-pre-wrap font-serif">
          {article.content}
        </div>

        <div className="pt-8 border-t border-border/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex flex-wrap gap-2">
            {article.tags?.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs bg-card">#{tag}</Badge>
            ))}
          </div>
          
          {article.url && (
            <a href={article.url} target="_blank" rel="noopener noreferrer">
              <Button variant="default" className="w-full sm:w-auto">
                Đọc bài gốc trên {article.source_name}
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
            </a>
          )}
        </div>
      </article>
    </div>
  );
}
