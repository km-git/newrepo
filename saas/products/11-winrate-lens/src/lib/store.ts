import type { Quote } from "./types";
import { computeMetrics } from "./metrics";
import { generateMonthlyInsight } from "./narrative";
import { getDemoQuotes, mockServiceM8Sync } from "./sync-adapter";

const globalStore = globalThis as typeof globalThis & {
  __wrlStore?: {
    quotes: Map<string, Quote>;
    lastSyncAt?: string;
  };
};

function store() {
  if (!globalStore.__wrlStore) {
    const quotes = new Map<string, Quote>();
    for (const q of getDemoQuotes()) {
      quotes.set(q.id, q);
    }
    globalStore.__wrlStore = {
      quotes,
      lastSyncAt: new Date().toISOString(),
    };
  }
  return globalStore.__wrlStore;
}

export function listQuotes(): Quote[] {
  return [...store().quotes.values()].sort(
    (a, b) => new Date(b.quotedAt).getTime() - new Date(a.quotedAt).getTime(),
  );
}

export function getMetrics() {
  return computeMetrics(listQuotes());
}

export function getInsight() {
  return generateMonthlyInsight(getMetrics());
}

export function syncFromServiceM8() {
  const result = mockServiceM8Sync();
  if (result.mockMode) {
    for (const q of getDemoQuotes()) {
      store().quotes.set(q.id, q);
    }
    store().lastSyncAt = new Date().toISOString();
  }
  return { ...result, lastSyncAt: store().lastSyncAt };
}

export function getLastSyncAt(): string | undefined {
  return store().lastSyncAt;
}

export function isMockMode(): boolean {
  return !process.env.SERVICEM8_API_KEY;
}

export function resetStore(): void {
  globalStore.__wrlStore = undefined;
}
