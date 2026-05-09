"use client";

export function KPICardsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="border border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm rounded-xl p-6 space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="h-4 w-24 bg-muted animate-pulse rounded" />
            <div className="h-9 w-9 bg-muted animate-pulse rounded-lg" />
          </div>
          <div className="h-8 w-36 bg-muted animate-pulse rounded" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="border border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm rounded-xl p-6 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-5 w-5 bg-amber-500/20 animate-pulse rounded" />
        <div className="h-5 w-40 bg-muted animate-pulse rounded" />
      </div>
      <div className="flex-1 min-h-[300px] flex items-end gap-1 px-4 pb-4">
        {Array.from({ length: 20 }).map((_, i) => {
          const height = 30 + Math.random() * 60;
          return (
            <div
              key={i}
              className="flex-1 bg-muted/50 animate-pulse rounded-t"
              style={{
                height: `${height}%`,
                animationDelay: `${i * 50}ms`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

export function TechnicalIndicatorsSkeleton() {
  return (
    <div className="border border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm rounded-xl p-6 h-full flex flex-col space-y-6">
      <div className="flex items-center gap-2">
        <div className="h-5 w-5 bg-amber-500/20 animate-pulse rounded" />
        <div className="h-5 w-36 bg-muted animate-pulse rounded" />
      </div>
      <div className="bg-background/50 p-4 rounded-xl border border-border/50 space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-4 w-24 bg-muted animate-pulse rounded" />
          <div className="h-6 w-20 bg-muted animate-pulse rounded-full" />
        </div>
        <div className="h-1.5 w-full bg-muted animate-pulse rounded-full" />
        <div className="h-10 w-20 mx-auto bg-muted animate-pulse rounded" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-14 bg-muted/30 animate-pulse rounded-lg border border-border/50"
            style={{ animationDelay: `${i * 100}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

export function MarketOverviewSkeleton() {
  return (
    <div className="border border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm rounded-xl overflow-hidden">
      <div className="p-4 border-b border-border/50 bg-card/50">
        <div className="h-6 w-48 bg-muted animate-pulse rounded" />
        <div className="h-4 w-72 bg-muted/60 animate-pulse rounded mt-2" />
      </div>
      <div className="p-4 space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 py-3 px-2 rounded-lg"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="h-8 w-1 bg-muted animate-pulse rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="h-5 w-36 bg-muted animate-pulse rounded" />
              <div className="h-4 w-24 bg-muted/60 animate-pulse rounded" />
            </div>
            <div className="h-5 w-28 bg-muted animate-pulse rounded" />
            <div className="h-5 w-28 bg-muted animate-pulse rounded" />
            <div className="h-5 w-20 bg-muted animate-pulse rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function NewsKpiSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="border border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm rounded-xl p-6 space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="h-4 w-32 bg-muted animate-pulse rounded" />
            <div className="h-9 w-9 bg-muted animate-pulse rounded-lg" />
          </div>
          <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          <div className="h-4 w-full bg-muted/40 animate-pulse rounded" />
        </div>
      ))}
    </div>
  );
}

export function NewsTableSkeleton() {
  return (
    <div className="border border-border/50 bg-gradient-to-br from-card to-card/50 shadow-sm backdrop-blur-sm rounded-xl overflow-hidden">
      <div className="p-4 border-b border-border/50 bg-card/50">
        <div className="h-6 w-44 bg-muted animate-pulse rounded" />
        <div className="h-4 w-64 bg-muted/60 animate-pulse rounded mt-2" />
      </div>
      <div className="p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 py-3"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="flex-1 space-y-2">
              <div className="h-5 w-3/4 bg-muted animate-pulse rounded" />
              <div className="h-4 w-1/2 bg-muted/60 animate-pulse rounded" />
            </div>
            <div className="h-6 w-16 bg-muted animate-pulse rounded-full" />
            <div className="h-6 w-16 bg-muted animate-pulse rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}
