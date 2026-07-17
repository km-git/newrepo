import type { Quote, ThreadState } from "./types";

const STALE_DAYS = 3;

export function daysSince(isoDate: string): number {
  const ms = Date.now() - new Date(isoDate).getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

export function classifyThreadState(
  lastCustomerReplyAt: string | undefined,
  status: Quote["status"],
): ThreadState {
  if (status === "won" || status === "lost") return "closed";
  if (lastCustomerReplyAt) return "customer_replied";
  return "awaiting_reply";
}

export function detectStaleQuotes(quotes: Quote[]): Quote[] {
  return quotes.filter(
    (q) =>
      q.threadState === "awaiting_reply" &&
      q.status !== "won" &&
      q.status !== "lost" &&
      q.daysSinceSent >= STALE_DAYS,
  );
}

export function needsFollowUp(quote: Quote): boolean {
  return (
    quote.threadState === "awaiting_reply" &&
    quote.status !== "won" &&
    quote.status !== "lost" &&
    quote.daysSinceSent >= STALE_DAYS
  );
}

export function enrichQuote(
  q: Omit<Quote, "daysSinceSent" | "threadState">,
): Quote {
  const daysSinceSent = daysSince(q.sentAt);
  const threadState = classifyThreadState(q.lastCustomerReplyAt, q.status);
  const status =
    threadState === "awaiting_reply" && daysSinceSent >= STALE_DAYS && q.status === "sent"
      ? "stale"
      : q.status;
  return { ...q, daysSinceSent, threadState, status };
}
