"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ShieldAlert, Zap } from "lucide-react";

interface ContextPanelProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  sources: any;
}

export function ContextPanel({ sources }: ContextPanelProps) {
  if (!sources) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-6 text-center">
        <ShieldAlert className="h-10 w-10 mb-4 text-muted-foreground/30" />
        <p className="text-sm">Chưa có dữ liệu ngữ cảnh.</p>
        <p className="text-xs mt-2">Dữ liệu tham khảo sẽ xuất hiện ở đây sau khi bạn hỏi.</p>
      </div>
    );
  }

  const { price, news, evidence_grade, route } = sources;

  return (
    <div className="flex flex-col h-full bg-card border-l">
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="font-semibold text-base flex items-center gap-2">
          <Zap className="h-5 w-5 text-amber-500" /> Ngữ cảnh truy xuất
        </h3>
        {route && (
          <Badge variant="outline" className="text-xs px-2 h-6 capitalize">
            Intent: {route.intent}
          </Badge>
        )}
      </div>

      <Tabs defaultValue="evidence" className="flex-1 flex flex-col">
        <div className="px-4 pt-3">
          <TabsList className="w-full grid grid-cols-3 h-10">
            <TabsTrigger value="evidence" className="text-sm">Đánh giá</TabsTrigger>
            <TabsTrigger value="news" className="text-sm">Tin tức</TabsTrigger>
            <TabsTrigger value="price" className="text-sm">Dữ liệu giá</TabsTrigger>
          </TabsList>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-4">
            
            {/* EVIDENCE TAB */}
            <TabsContent value="evidence" className="mt-0 space-y-4">
              {evidence_grade ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Mức độ tự tin:</span>
                    <Badge variant={
                      evidence_grade.confidence === "high" ? "default" : 
                      evidence_grade.confidence === "medium" ? "secondary" : "destructive"
                    } className={evidence_grade.confidence === "high" ? "bg-emerald-500 hover:bg-emerald-600 text-sm py-0.5 px-2" : "text-sm py-0.5 px-2"}>
                      {evidence_grade.confidence.toUpperCase()}
                    </Badge>
                  </div>
                  
                  <div>
                    <span className="text-sm font-medium text-muted-foreground">Có thể giải thích nguyên nhân:</span>
                    <span className={`ml-2 text-base font-medium ${evidence_grade.can_explain_cause ? 'text-emerald-500' : 'text-red-500'}`}>
                      {evidence_grade.can_explain_cause ? "CÓ" : "KHÔNG"}
                    </span>
                  </div>

                  <div className="space-y-2">
                    <span className="text-sm font-medium text-muted-foreground">Lý do:</span>
                    <p className="text-sm bg-muted p-2.5 rounded-md border leading-relaxed">
                      {evidence_grade.reason || "Không có lý do chi tiết."}
                    </p>
                  </div>

                  {evidence_grade.missing_data && evidence_grade.missing_data.length > 0 && (
                    <div className="space-y-2 pt-2 border-t">
                      <span className="text-sm font-medium text-red-500">Dữ liệu còn thiếu:</span>
                      <div className="flex flex-wrap gap-1">
                        {evidence_grade.missing_data.map((item: string, i: number) => (
                          <Badge key={i} variant="outline" className="text-xs px-2 text-red-400 border-red-500/20 bg-red-500/10">
                            {item}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Không có dữ liệu đánh giá bằng chứng.</p>
              )}
            </TabsContent>

            {/* NEWS TAB */}
            <TabsContent value="news" className="mt-0 space-y-3">
              {news && news.articles && news.articles.length > 0 ? (
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                news.articles.map((article: any, i: number) => (
                  <Card key={i} className="border bg-card/50 shadow-none">
                    <CardContent className="p-3 space-y-2">
                      <h4 className="text-base font-medium line-clamp-2 leading-tight">
                        {article.title}
                      </h4>
                      <div className="flex items-center justify-between mt-2">
                        <Badge variant="outline" className="text-xs h-5 px-2 font-normal">
                          {article.source_name}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {article.published_at ? article.published_at.substring(0, 10) : ""}
                        </span>
                      </div>
                      {article.impact_score !== undefined && (
                        <div className="flex items-center justify-between pt-2">
                          <span className="text-xs text-muted-foreground">Impact</span>
                          <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-amber-500" 
                              style={{ width: `${article.impact_score * 100}%` }} 
                            />
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-xs text-muted-foreground text-center py-4">Không có tin tức nào được truy xuất.</p>
              )}
            </TabsContent>

            {/* PRICE TAB */}
            <TabsContent value="price" className="mt-0 space-y-3">
              {price && price.ok ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-muted p-3 rounded-md">
                      <span className="text-xs text-muted-foreground block mb-1">Mã vàng</span>
                      <span className="text-sm font-bold">{price.type_code || "N/A"}</span>
                    </div>
                    <div className="bg-muted p-3 rounded-md">
                      <span className="text-xs text-muted-foreground block mb-1">Xu hướng</span>
                      <span className="text-sm font-bold capitalize">{price.trend || "N/A"}</span>
                    </div>
                  </div>

                  {price.change !== undefined && (
                    <div className="flex items-center justify-between border-b pb-3">
                      <span className="text-sm text-muted-foreground">Thay đổi</span>
                      <span className={`text-base font-bold tabular-nums ${price.change > 0 ? 'text-emerald-500' : price.change < 0 ? 'text-red-500' : ''}`}>
                        {price.change > 0 ? '+' : ''}{new Intl.NumberFormat('vi-VN').format(price.change)} đ
                      </span>
                    </div>
                  )}

                  {price.rsi14 !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">RSI (14 ngày)</span>
                      <div className="text-right">
                        <span className="text-base font-bold tabular-nums block">{Number(price.rsi14).toFixed(1)}</span>
                        <span className="text-xs text-muted-foreground">{price.rsi_summary}</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-4">Không truy xuất được dữ liệu giá.</p>
              )}
            </TabsContent>

          </div>
        </ScrollArea>
      </Tabs>
    </div>
  );
}
