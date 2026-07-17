import { describe, it, expect, beforeEach } from "vitest";
import {
  priceBand,
  responseBucket,
  winRate,
  computeMetrics,
  computeResponseHours,
} from "./metrics";
import { generateMonthlyInsight } from "./narrative";
import { getDemoQuotes } from "./sync-adapter";
import {
  resetStore,
  listQuotes,
  getMetrics,
  getInsight,
  syncFromServiceM8,
  isMockMode,
} from "./store";
import type { Quote } from "./types";

describe("metrics", () => {
  it("classifies price bands", () => {
    expect(priceBand(300)).toBe("under_500");
    expect(priceBand(800)).toBe("500_1500");
    expect(priceBand(3000)).toBe("1500_5000");
    expect(priceBand(6000)).toBe("over_5000");
  });

  it("classifies response buckets", () => {
    expect(responseBucket(2)).toBe("under_4h");
    expect(responseBucket(12)).toBe("4_24h");
    expect(responseBucket(30)).toBe("over_24h");
  });

  it("computes win rate", () => {
    expect(winRate(3, 1)).toBe(75);
    expect(winRate(0, 0)).toBe(0);
  });

  it("computes response hours", () => {
    const hours = computeResponseHours(
      "2026-06-01T09:00:00Z",
      "2026-06-01T11:30:00Z",
    );
    expect(hours).toBe(2.5);
  });

  it("aggregates metrics by dimension", () => {
    const metrics = computeMetrics(getDemoQuotes());
    expect(metrics.overall.won + metrics.overall.lost).toBeGreaterThan(0);
    expect(metrics.byJobType.length).toBeGreaterThan(0);
    expect(metrics.bySuburb.length).toBeGreaterThan(0);
    expect(metrics.byPriceBand.length).toBeGreaterThan(0);
  });
});

describe("narrative", () => {
  it("generates plain-English insight", () => {
    const insight = generateMonthlyInsight(computeMetrics(getDemoQuotes()));
    expect(insight.headline.length).toBeGreaterThan(10);
    expect(insight.bullets.length).toBeGreaterThanOrEqual(2);
    expect(insight.topOpportunity).toContain("Push");
    expect(insight.caution.length).toBeGreaterThan(10);
  });
});

describe("store", () => {
  beforeEach(() => resetStore());

  it("loads demo quotes", () => {
    expect(listQuotes().length).toBe(10);
  });

  it("computes dashboard metrics", () => {
    const metrics = getMetrics();
    expect(metrics.overall.winRate).toBeGreaterThan(0);
  });

  it("returns monthly insight", () => {
    const insight = getInsight();
    expect(insight.period).toBeTruthy();
  });

  it("syncs in mock mode", () => {
    expect(isMockMode()).toBe(true);
    const result = syncFromServiceM8();
    expect(result.mockMode).toBe(true);
    expect(result.imported).toBe(10);
  });
});

describe("demo data quality", () => {
  it("has mixed outcomes for analysis", () => {
    const quotes: Quote[] = getDemoQuotes();
    const won = quotes.filter((q) => q.status === "won").length;
    const lost = quotes.filter((q) => q.status === "lost").length;
    expect(won).toBeGreaterThan(0);
    expect(lost).toBeGreaterThan(0);
  });
});
