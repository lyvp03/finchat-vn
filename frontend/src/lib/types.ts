export interface PriceData {
  ts: string;
  type_code: string;
  metadata: { name: string; market: string; unit: string };
  brand: string;
  gold_type: string;
  buy_price: number;
  sell_price: number;
  mid_price: number;
  spread: number;
  daily_return_pct: number;
}

export interface LatestPriceResponse {
  ok: boolean;
  count: number;
  prices: PriceData[];
}

export interface PriceHistoryResponse {
  ok: boolean;
  type: string;
  type_code: string;
  metadata: { name: string; market: string; unit: string };
  period_days: number;
  from: string;
  to: string;
  start_mid_price: number;
  latest: PriceData;
  change: number;
  change_pct: number;
  trend: string;
  rsi14: number;
  rsi_summary: string;
  top_moves: Array<{
    ts: string;
    mid_price: number;
    price_change: number;
  }>;
}

export interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  source_name: string;
  market_scope: string;
  event_type: string;
  sentiment_score: number;
  impact_score: number;
  published_at: string;
  url?: string;
}

export interface LatestNewsResponse {
  ok: boolean;
  articles: NewsArticle[];
}

export interface ChatRequest {
  message: string;
  history: Array<{ role: string; content: string }>;
}

export interface ChatResponse {
  response: string;
  intent: string;
  sources: unknown;
}

export interface PriceTimeseriesPoint {
  ts: string;
  buy_price: number;
  sell_price: number;
  mid_price: number;
}

export interface PriceTimeseriesResponse {
  ok: boolean;
  type_code: string;
  days: number;
  data: PriceTimeseriesPoint[];
}

export interface NewsSummaryResponse {
  ok: boolean;
  days: number;
  total: number;
  avg_sentiment: number;
  avg_impact: number;
  top_event_types: Array<{ event_type: string; count: number }>;
  count_by_scope: Array<{ market_scope: string; count: number }>;
}

export interface NewsDetailResponse {
  ok: boolean;
  article: NewsArticle & {
    content: string;
    tags: string[];
    news_tier: string;
  };
}

export interface EvalScores {
  correctness: number;
  insight: number;
  clarity: number;
  naturalness: number;
  conciseness: number;
  final_score: number;
}

export interface EvalResponse {
  ok: boolean;
  scores?: EvalScores;
  error?: string;
}
