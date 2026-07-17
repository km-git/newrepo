import { describe, it, expect, beforeEach } from "vitest";
import { needsFollowUp, detectStaleQuotes, enrichQuote } from "./quote-detector";
import { stageForDays, toneForStage, isDueForFollowUp } from "./follow-up-cadence";
import { draftFollowUp } from "./follow-up-drafter";
import {
  resetStore,
  listQuotes,
  listStaleQuotes,
  generateDraft,
  approveAndSend,
  getSettings,
  pendingCount,
  isMockMode,
} from "./store";
import type { Quote } from "./types";

describe("quote-detector", () => {
  const base: Omit<Quote, "daysSinceSent" | "threadState"> = {
    id: "q1",
    quoteNumber: "Q-100",
    contactName: "Test User",
    contactEmail: "test@example.com",
    jobDescription: "Tap repair",
    amountAud: 400,
    sentAt: new Date(Date.now() - 5 * 86400000).toISOString(),
    status: "sent",
    source: "email",
  };

  it("detects stale unanswered quotes", () => {
    const q = enrichQuote(base);
    expect(needsFollowUp(q)).toBe(true);
    expect(q.status).toBe("stale");
  });

  it("skips quotes with customer replies", () => {
    const q = enrichQuote({
      ...base,
      lastCustomerReplyAt: new Date().toISOString(),
    });
    expect(q.threadState).toBe("customer_replied");
    expect(needsFollowUp(q)).toBe(false);
  });
});

describe("follow-up-cadence", () => {
  it("maps days to stages", () => {
    expect(stageForDays(3)).toBe(1);
    expect(stageForDays(7)).toBe(2);
    expect(stageForDays(14)).toBe(3);
  });

  it("assigns tones by stage", () => {
    expect(toneForStage(1)).toBe("gentle");
    expect(toneForStage(3)).toBe("firm");
  });

  it("checks follow-up due", () => {
    expect(isDueForFollowUp(5, 0)).toBe(true);
    expect(isDueForFollowUp(5, 1)).toBe(false);
  });
});

describe("follow-up-drafter", () => {
  it("drafts on-brand follow-up", () => {
    const quote = enrichQuote({
      id: "q1",
      quoteNumber: "Q-100",
      contactName: "Sarah Mitchell",
      contactEmail: "sarah@example.com",
      jobDescription: "Tap repair",
      amountAud: 400,
      sentAt: new Date(Date.now() - 5 * 86400000).toISOString(),
      status: "sent",
      source: "email",
    });
    const draft = draftFollowUp(quote, 1, "RapidFlow", "Alex", "seq-1");
    expect(draft.subject).toContain("Q-100");
    expect(draft.body).toContain("Sarah");
    expect(draft.body).toContain("RapidFlow");
  });
});

describe("store", () => {
  beforeEach(() => resetStore());

  it("loads demo quotes", () => {
    expect(listQuotes().length).toBe(6);
  });

  it("finds stale quotes needing chase", () => {
    const stale = listStaleQuotes();
    expect(stale.length).toBeGreaterThan(0);
    expect(stale.every((q) => q.daysSinceSent >= 3)).toBe(true);
  });

  it("generates draft for stale quote", () => {
    const stale = listStaleQuotes();
    const draft = generateDraft(stale[0].id);
    expect(draft).toBeDefined();
    expect(draft!.status).toBe("draft");
    expect(pendingCount()).toBeGreaterThan(0);
  });

  it("sends after approval", () => {
    const stale = listStaleQuotes();
    const draft = generateDraft(stale[0].id)!;
    const { result } = approveAndSend(draft.id)!;
    expect(result.success).toBe(true);
    expect(draft.status).toBe("sent");
  });

  it("uses business settings", () => {
    expect(getSettings().followUpCadenceDays).toEqual([3, 7, 14]);
  });

  it("runs in mock mode", () => {
    expect(isMockMode()).toBe(true);
  });
});

describe("stale detection batch", () => {
  beforeEach(() => resetStore());

  it("excludes won quotes", () => {
    const stale = detectStaleQuotes(listQuotes());
    expect(stale.every((q) => q.status !== "won")).toBe(true);
  });
});
