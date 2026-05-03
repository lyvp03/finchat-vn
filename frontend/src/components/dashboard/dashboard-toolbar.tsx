"use client";

import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeftRight, Check, ChevronsUpDown, LayoutTemplate } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";
import { useState } from "react";

export type DashboardMode = "single" | "compare";
export type TimeRange = "7D" | "30D" | "90D" | "6M";

export const AVAILABLE_ASSETS = [
  { id: "SJL1L10", name: "Vàng miếng SJC", market: "SJC" },
  { id: "SJ9999", name: "Vàng nhẫn SJC 9999", market: "SJC" },
  { id: "DOHCML", name: "Vàng SJC DOJI (HCM)", market: "DOJI" },
  { id: "DOHNL", name: "Vàng SJC DOJI (HN)", market: "DOJI" },
  { id: "BTSJC", name: "Vàng SJC BTMC", market: "BTMC" },
  { id: "XAUUSD", name: "Gold Spot", market: "International" },
];

interface DashboardToolbarProps {
  mode: DashboardMode;
  setMode: (mode: DashboardMode) => void;
  primaryAsset: string;
  setPrimaryAsset: (asset: string) => void;
  compareAssets: string[];
  setCompareAssets: (assets: string[]) => void;
  timeRange: TimeRange;
  setTimeRange: (range: TimeRange) => void;
}

export function DashboardToolbar({
  mode,
  setMode,
  primaryAsset,
  setPrimaryAsset,
  compareAssets,
  setCompareAssets,
  timeRange,
  setTimeRange,
}: DashboardToolbarProps) {
  const [openAssetSelector, setOpenAssetSelector] = useState(false);

  const toggleCompareAsset = (assetId: string) => {
    if (compareAssets.includes(assetId)) {
      setCompareAssets(compareAssets.filter((a) => a !== assetId));
    } else {
      if (compareAssets.length < 4) {
        setCompareAssets([...compareAssets, assetId]);
      }
    }
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-card/50 p-3 rounded-2xl border border-border/50 backdrop-blur-sm shadow-sm mb-6">

      {/* Left side: Assets Selection */}
      <div className="flex items-center gap-3 w-full sm:w-auto">
        <div className="flex bg-background/50 rounded-lg p-1 border border-border/50">
          <Button
            variant="ghost"
            size="sm"
            className={cn("h-8 rounded-md px-3 text-xs font-medium", mode === "single" ? "bg-card shadow-sm text-primary" : "text-muted-foreground")}
            onClick={() => {
              setMode("single");
              if (!compareAssets.includes(primaryAsset)) {
                setCompareAssets([primaryAsset]);
              }
            }}
          >
            <LayoutTemplate className="w-3.5 h-3.5 mr-1.5" />
            Phân tích
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={cn("h-8 rounded-md px-3 text-xs font-medium", mode === "compare" ? "bg-card shadow-sm text-primary" : "text-muted-foreground")}
            onClick={() => setMode("compare")}
          >
            <ArrowLeftRight className="w-3.5 h-3.5 mr-1.5" />
            So sánh
          </Button>
        </div>

        <Popover open={openAssetSelector} onOpenChange={setOpenAssetSelector}>
          <PopoverTrigger
            className={cn(
              buttonVariants({ variant: "outline" }),
              "h-10 justify-between min-w-[200px] border-border/50 bg-background/50 hover:bg-muted/50"
            )}
          >
            {mode === "single" ? (
              <span>{AVAILABLE_ASSETS.find((a) => a.id === primaryAsset)?.name || "Chọn mã..."}</span>
            ) : (
              <span>
                {compareAssets.length} tài sản được chọn
              </span>
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </PopoverTrigger>
          <PopoverContent className="w-[250px] p-0" align="start">
            <Command>
              <CommandInput placeholder="Tìm kiếm mã tài sản..." />
              <CommandList>
                <CommandEmpty>Không tìm thấy.</CommandEmpty>
                <CommandGroup>
                  {AVAILABLE_ASSETS.map((asset) => (
                    <CommandItem
                      key={asset.id}
                      value={asset.name}
                      onSelect={() => {
                        if (mode === "single") {
                          setPrimaryAsset(asset.id);
                          setOpenAssetSelector(false);
                        } else {
                          toggleCompareAsset(asset.id);
                        }
                      }}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          (mode === "single" ? primaryAsset === asset.id : compareAssets.includes(asset.id))
                            ? "opacity-100 text-primary"
                            : "opacity-0"
                        )}
                      />
                      <div className="flex flex-col">
                        <span>{asset.name}</span>
                        <span className="text-[10px] text-muted-foreground">{asset.id}</span>
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>

        {mode === "compare" && (
          <div className="hidden lg:flex items-center gap-1.5">
            {compareAssets.map(assetId => {
              const asset = AVAILABLE_ASSETS.find(a => a.id === assetId);
              return asset ? (
                <Badge key={assetId} variant="secondary" className="bg-background/80 border-border/50 font-normal">
                  {asset.market} {asset.id.replace(asset.market, '')}
                  <button
                    className="ml-1 text-muted-foreground hover:text-foreground"
                    onClick={() => toggleCompareAsset(assetId)}
                  >
                    &times;
                  </button>
                </Badge>
              ) : null;
            })}
          </div>
        )}
      </div>

      {/* Right side: Time Range */}
      <div className="flex bg-background/50 rounded-lg p-1 border border-border/50 w-full sm:w-auto overflow-x-auto">
        {(["7D", "30D", "90D", "6M"] as TimeRange[]).map((range) => (
          <Button
            key={range}
            variant="ghost"
            size="sm"
            className={cn(
              "h-8 rounded-md px-3 text-xs font-medium min-w-[50px]",
              timeRange === range ? "bg-card shadow-sm text-foreground" : "text-muted-foreground"
            )}
            onClick={() => setTimeRange(range)}
          >
            {range}
          </Button>
        ))}
      </div>
    </div>
  );
}
