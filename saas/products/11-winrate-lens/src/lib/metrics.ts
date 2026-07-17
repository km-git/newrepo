import type { PriceBand, Quote, ResponseBucket } from "./types";

export function priceBand(amount: number): PriceBand {
  if (amount < 500) return "under_500";
  if (amount < 1500) return "500_1500";
  if (amount < 5000) return "1500_5000";
  return "over_5000";
}

export const PRICE_BAND_LABELS: Record<PriceBand, string> = {
  under_500: "Under $500",
  "500_1500": "$500–$1,500",
  "1500_5000": "$1,500–$5,000",
  over_5000: "Over $5,000",
};

export function responseBucket(hours: number | undefined): ResponseBucket {
  if (hours === undefined) return "over_24h";
  if (hours < 4) return "under_4h";
  if (hours <= 24) return "4_24h";
  return "over_24h";
}

export const RESPONSE_LABELS: Record<ResponseBucket, string> = {
  under_4h: "Under 4 hours",
  "4_24h": "4–24 hours",
  over_24h: "Over 24 hours",
};

export function computeResponseHours(quotedAt: string, respondedAt?: string): number | undefined {
  if (!respondedAt) return undefined;
  const ms = new Date(respondedAt).getTime() - new Date(quotedAt).getTime();
  return Math.max(0, ms / (1000 * 60 * 60));
}

export function winRate(won: number, lost: number): number {
  const decided = won + lost;
  if (decided === 0) return 0;
  return Math.round((won / decided) * 100);
}

export function groupQuotes(
  quotes: Quote[],
  keyFn: (q: Quote) => string,
  labelFn: (key: string) => string,
) {
  const groups = new Map<string, Quote[]>();
  for (const q of quotes) {
    const key = keyFn(q);
    const list = groups.get(key) ?? [];
    list.push(q);
    groups.set(key, list);
  }

  return [...groups.entries()]
    .map(([key, items]) => {
      const won = items.filter((q) => q.status === "won");
      const lost = items.filter((q) => q.status === "lost");
      const open = items.filter((q) => q.status === "open");
      return {
        key,
        label: labelFn(key),
        won: won.length,
        lost: lost.length,
        open: open.length,
        winRate: winRate(won.length, lost.length),
        totalValueWon: won.reduce((s, q) => s + q.amountAud, 0),
      };
    })
    .sort((a, b) => b.winRate - a.winRate);
}

export function computeMetrics(quotes: Quote[], period = "Last 90 days"): import("./types").WinRateMetrics {
  const decided = quotes.filter((q) => q.status !== "open");
  const won = quotes.filter((q) => q.status === "won");
  const lost = quotes.filter((q) => q.status === "lost");
  const open = quotes.filter((q) => q.status === "open");

  const withResponse = quotes.filter((q) => q.responseHours !== undefined);
  const avgResponseHours =
    withResponse.length === 0
      ? 0
      : Math.round(
          (withResponse.reduce((s, q) => s + (q.responseHours ?? 0), 0) / withResponse.length) * 10,
        ) / 10;

  return {
    period,
    overall: {
      key: "all",
      label: "All quotes",
      won: won.length,
      lost: lost.length,
      open: open.length,
      winRate: winRate(won.length, lost.length),
      totalValueWon: won.reduce((s, q) => s + q.amountAud, 0),
    },
    byJobType: groupQuotes(decided, (q) => q.jobType, (k) => k),
    bySuburb: groupQuotes(decided, (q) => q.suburb, (k) => k),
    byPriceBand: groupQuotes(decided, (q) => priceBand(q.amountAud), (k) => PRICE_BAND_LABELS[k as PriceBand] ?? k),
    byResponseTime: groupQuotes(
      decided.filter((q) => q.responseHours !== undefined),
      (q) => responseBucket(q.responseHours),
      (k) => RESPONSE_LABELS[k as ResponseBucket] ?? k,
    ),
    avgResponseHours,
    totalQuoted: quotes.reduce((s, q) => s + q.amountAud, 0),
  };
}
