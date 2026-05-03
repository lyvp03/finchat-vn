"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { NewsArticle } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { useRouter } from "next/navigation";

interface RecentNewsTableProps {
  newsData: NewsArticle[];
}

export function RecentNewsTable({ newsData }: RecentNewsTableProps) {
  const router = useRouter();
  
  const getSentimentIcon = (score: number) => {
    if (score > 0.1) return <ArrowUpRight className="h-4 w-4 text-emerald-500" />;
    if (score < -0.1) return <ArrowDownRight className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-muted-foreground" />;
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.1) return "text-emerald-500 bg-emerald-500/10";
    if (score < -0.1) return "text-red-500 bg-red-500/10";
    return "text-muted-foreground bg-muted";
  };

  return (
    <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm overflow-hidden flex flex-col h-full">
      <CardHeader className="border-b border-border/50 bg-card/50">
        <CardTitle className="flex items-center gap-2 text-lg">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/></svg>
          Tin Tức Đáng Chú Ý
        </CardTitle>
        <CardDescription>Các sự kiện có mức độ ảnh hưởng cao tới thị trường vàng</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="w-full">
          <Table>
            <TableHeader className="bg-background/50">
              <TableRow className="hover:bg-transparent border-border/50">
                <TableHead className="w-[400px] text-muted-foreground font-medium">Tiêu đề</TableHead>
                <TableHead className="text-muted-foreground font-medium">Nguồn</TableHead>
                <TableHead className="text-muted-foreground font-medium">Sự kiện</TableHead>
                <TableHead className="text-muted-foreground font-medium">Tác động</TableHead>
                <TableHead className="text-muted-foreground font-medium">Tín hiệu</TableHead>
                <TableHead className="text-right text-muted-foreground font-medium">Ngày</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {newsData.length === 0 ? (
                <TableRow className="border-border/50 hover:bg-muted/50">
                  <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                    Không có tin tức nào gần đây.
                  </TableCell>
                </TableRow>
              ) : (
                newsData.map((article) => (
                  <TableRow 
                    key={article.id} 
                    className="border-border/50 hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => router.push(`/news/${article.id}`)}
                  >
                    <TableCell className="font-medium text-foreground">
                      <div className="line-clamp-2" title={article.title}>
                        {article.title}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {article.source_name}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="font-normal">
                        {article.event_type.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={article.impact_score * 100} className="h-2 w-16" />
                        <span className="text-xs text-muted-foreground">{(article.impact_score * 100).toFixed(0)}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className={`flex items-center gap-1 px-2 py-1 rounded-md w-fit text-xs font-medium ${getSentimentColor(article.sentiment_score)}`}>
                        {getSentimentIcon(article.sentiment_score)}
                        {article.sentiment_score > 0.1 ? "Tích cực" : article.sentiment_score < -0.1 ? "Tiêu cực" : "Trung lập"}
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(article.published_at).toLocaleDateString("vi-VN", { 
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" 
                      })}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
