"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { LatestPriceResponse, PriceHistoryResponse } from "@/lib/types";
import { DashboardMode, AVAILABLE_ASSETS } from "./dashboard-toolbar";
import { Checkbox } from "@/components/ui/checkbox";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

interface MarketOverviewTableProps {
  latestPrice: LatestPriceResponse;
  priceHistories: PriceHistoryResponse[];
  mode: DashboardMode;
  primaryAsset: string;
  setPrimaryAsset: (asset: string) => void;
  compareAssets: string[];
  setCompareAssets: (assets: string[]) => void;
}

export function MarketOverviewTable({ 
  latestPrice, 
  priceHistories,
  mode, 
  primaryAsset, 
  setPrimaryAsset, 
  compareAssets, 
  setCompareAssets 
}: MarketOverviewTableProps) {
  
  const formatCurrency = (val: number, unit: string) => {
    const formatted = new Intl.NumberFormat('vi-VN').format(val);
    return `${formatted} ${unit === 'USD/oz' ? 'USD' : 'VND'}`;
  };

  const toggleCompare = (asset: string) => {
    if (compareAssets.includes(asset)) {
      setCompareAssets(compareAssets.filter(a => a !== asset));
    } else if (compareAssets.length < 4) {
      setCompareAssets([...compareAssets, asset]);
    }
  };

  return (
    <Card className="border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm overflow-hidden">
      <CardHeader className="pb-3 border-b border-border/50 bg-card/50">
        <CardTitle className="text-lg">Toàn cảnh thị trường</CardTitle>
        <CardDescription>
          {mode === "single" ? "Nhấp vào một tài sản để phân tích chi tiết" : "Chọn các tài sản (tối đa 4) để so sánh"}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-background/50">
              <TableRow className="hover:bg-transparent border-border/50">
                {mode === "compare" && <TableHead className="w-[50px]"></TableHead>}
                <TableHead className="text-foreground font-semibold text-sm">Tài sản</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Mua vào</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Bán ra</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm hidden sm:table-cell">Chênh lệch</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm">Biến động</TableHead>
                <TableHead className="text-right text-foreground font-semibold text-sm hidden md:table-cell">Cập nhật</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {latestPrice.prices.map((item) => {
                const isSelected = mode === "single" ? item.type_code === primaryAsset : compareAssets.includes(item.type_code);
                
                // Get history to extract accurate change_pct
                const history = priceHistories.find(h => h.type_code === item.type_code);
                const pctValue = history?.change_pct ?? item.daily_return_pct;
                const isPositive = pctValue > 0;
                const isNegative = pctValue < 0;
                
                return (
                  <TableRow 
                    key={item.type_code} 
                    className={`border-border/50 transition-colors cursor-pointer ${
                      isSelected ? "bg-primary/5 hover:bg-primary/10" : "hover:bg-muted/50"
                    }`}
                    onClick={() => {
                      if (mode === "single") setPrimaryAsset(item.type_code);
                      else toggleCompare(item.type_code);
                    }}
                  >
                    {mode === "compare" && (
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Checkbox 
                          checked={isSelected} 
                          onCheckedChange={() => toggleCompare(item.type_code)}
                          disabled={!isSelected && compareAssets.length >= 4}
                          className="border-muted-foreground/50 data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                        />
                      </TableCell>
                    )}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className={`w-1 h-8 rounded-full ${isSelected ? "bg-primary" : "bg-transparent"}`}></div>
                        <div>
                          <div className={`font-semibold text-base ${isSelected ? "text-primary" : "text-foreground"}`}>
                            {AVAILABLE_ASSETS.find(a => a.id === item.type_code)?.name || item.metadata.name}
                          </div>
                          <div className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-xs h-5 px-2 font-medium capitalize border-border/50">
                              {item.metadata.market}
                            </Badge>
                            <span className="uppercase font-medium">{item.type_code}</span>
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-base font-semibold tabular-nums text-foreground">
                      {formatCurrency(history?.latest?.buy_price ?? item.buy_price, item.metadata.unit)}
                    </TableCell>
                    <TableCell className="text-right text-base font-semibold tabular-nums text-foreground">
                      {formatCurrency(history?.latest?.sell_price ?? item.sell_price, item.metadata.unit)}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground tabular-nums text-sm font-medium hidden sm:table-cell">
                      {new Intl.NumberFormat('vi-VN').format(history?.latest?.spread ?? item.spread)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-base">
                      <div className={`flex items-center justify-end gap-1 font-semibold ${
                        isPositive ? 'text-positive' : isNegative ? 'text-negative' : 'text-muted-foreground'
                      }`}>
                        {isPositive ? <ArrowUpRight className="h-4 w-4" /> : 
                         isNegative ? <ArrowDownRight className="h-4 w-4" /> : <Minus className="h-4 w-4" />}
                        {isPositive ? "+" : ""}{(pctValue || 0).toFixed(2)}%
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-sm text-muted-foreground tabular-nums hidden md:table-cell">
                      {new Date(item.ts).toLocaleDateString("vi-VN", { month: 'short', day: 'numeric', year: 'numeric' })}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
