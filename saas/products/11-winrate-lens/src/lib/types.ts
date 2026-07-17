export type QuoteStatus = "open" | "won" | "lost";

export type PriceBand = "under_500" | "500_1500" | "1500_5000" | "over_5000";

export type ResponseBucket = "under_4h" | "4_24h" | "over_24h";

export interface Quote {
  id: string;
  externalId: string;
  source: "servicem8" | "tradify" | "xero";
  jobType: string;
  suburb: string;
  amountAud: number;
  status: QuoteStatus;
  quotedAt: string;
  respondedAt?: string;
  closedAt?: string;
  responseHours?: number;
}

export interface WinRateSlice {
  key: string;
  label: string;
  won: number;
  lost: number;
  open: number;
  winRate: number;
  totalValueWon: number;
}

export interface WinRateMetrics {
  period: string;
  overall: WinRateSlice;
  byJobType: WinRateSlice[];
  bySuburb: WinRateSlice[];
  byPriceBand: WinRateSlice[];
  byResponseTime: WinRateSlice[];
  avgResponseHours: number;
  totalQuoted: number;
}

export interface MonthlyInsight {
  period: string;
  headline: string;
  bullets: string[];
  topOpportunity: string;
  caution: string;
}

export interface SyncResult {
  source: string;
  imported: number;
  updated: number;
  mockMode: boolean;
}
