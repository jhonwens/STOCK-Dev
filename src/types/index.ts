export interface StockSummary {
  total_stocks: number;
  total_holdings: number;
  total_pnl: number;
  alert_count: number;
  candidate_count: number;
  chan_signals: number;
}

export interface MarketMover {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  volume: number;
}

export interface MarketOverview {
  top_gainers: MarketMover[];
  top_losers: MarketMover[];
  last_update: string;
}

export interface StockListEntry {
  code: string;
  name: string;
  industry: string;
}

export interface StockItem {
  code: string;
  name: string;
  industry: string;
  price: number;
  change_pct: number;
  score: number;
  suggestion: string;
  risk_level: string;
}

export interface PortfolioStock {
  id: number;
  code: string;
  name: string;
  category: string;
  cost_price: number;
  shares: number;
  add_date: string;
  notes: string;
  price: number;
  change_pct: number;
  score: number;
  suggestion: string;
  risk_level: string;
}

export interface TechnicalIndicators {
  ema20?: number;
  ema60?: number;
  ema120?: number;
  multi_head?: boolean;
  macd: {
    DIF: number;
    DEA: number;
    hist: number;
    golden_cross: boolean;
    death_cross: boolean;
    above_zero: boolean;
  };
  kdj: {
    K: number;
    D: number;
    J: number;
    golden_cross: boolean;
    overbought: boolean;
  };
  rsi: {
    RSI: number;
    overbought: boolean;
    oversold: boolean;
  };
  boll: {
    upper: number;
    mid: number;
    lower: number;
    position: string;
    overbought: boolean;
  };
  obv: {
    OBV: number;
    trend: string;
  };
  [key: string]: any;
}

export interface IndustryGroup {
  industry: string;
  stocks: StockItem[];
}

export interface CandidateStock {
  rank: number;
  code: string;
  name: string;
  overall_score: number;
  recommend_reason: string;
  suggested_price_range: [number, number];
  risk_warning: string;
  holding_period: string;
  analysis_12dim: Record<string, string>;
}

export interface CandidateCategory {
  summary: string;
  top5: CandidateStock[];
}

export interface CandidateRecommendation {
  short_term: CandidateCategory;
  long_term: CandidateCategory;
}

export interface BuyPointLevel {
  point: string;
  price_range: [number, number];
  confidence: string;
  detail: string;
}

export interface BuyPointAnalysis {
  summary: string;
  short_term: BuyPointLevel;
  mid_term: BuyPointLevel;
  long_term: BuyPointLevel;
  position_suggestion: string;
  key_indicators: {
    support_level: number;
    resistance_level: number;
    stop_loss: number;
  };
}

export interface StockInsightResult {
  basic_info: {
    code: string;
    name: string;
    industry: string;
    price: number;
    change_pct: number;
    pe: number;
    pb: number;
  };
  buy_point_analysis: BuyPointAnalysis;
  analysis_12dim: Record<string, string>;
  risk_warning: string;
}

export interface StockSearchResult {
  code: string;
  name: string;
  industry: string;
}

// === License & Feature Flag Types ===

export type TierId = "free" | "pro" | "vip";

export interface TierLimits {
  max_holdings: number;
  max_watchlist: number;
  export_pro_report: boolean;
}

export interface LicenseInfo {
  key: string;
  tier: TierId;
  issued_at: string;
  expired_at: string;
  device_id: string;
}

export interface FeatureFlags {
  tier: TierId;
  limits: TierLimits;
  is_licensed: boolean;
  license: LicenseInfo | null;
}

export interface TierDef {
  id: TierId;
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
}