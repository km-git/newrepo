import { randomUUID } from "crypto";
import type {
  BusinessSettings,
  FollowUpDraft,
  FollowUpSequence,
  Quote,
} from "./types";
import { enrichQuote, detectStaleQuotes, needsFollowUp } from "./quote-detector";
import { isDueForFollowUp, stageForDays, nextActionDate } from "./follow-up-cadence";
import { draftFollowUp } from "./follow-up-drafter";
import { sendFollowUpEmail } from "./email-adapter";

const globalStore = globalThis as typeof globalThis & {
  __qcStore?: {
    settings: BusinessSettings;
    quotes: Map<string, Quote>;
    sequences: Map<string, FollowUpSequence>;
    drafts: Map<string, FollowUpDraft>;
  };
};

const DEMO_QUOTES: Omit<Quote, "daysSinceSent" | "threadState">[] = [
  {
    id: "qt-001",
    quoteNumber: "Q-1042",
    contactName: "Sarah Mitchell",
    contactEmail: "sarah@example.com",
    jobDescription: "Bathroom tap replacement",
    amountAud: 480,
    sentAt: new Date(Date.now() - 5 * 86400000).toISOString(),
    status: "sent",
    source: "email",
  },
  {
    id: "qt-002",
    quoteNumber: "Q-1043",
    contactName: "James Chen",
    contactEmail: "james@example.com",
    jobDescription: "Hot water system install",
    amountAud: 2200,
    sentAt: new Date(Date.now() - 8 * 86400000).toISOString(),
    status: "sent",
    source: "xero",
  },
  {
    id: "qt-003",
    quoteNumber: "Q-1044",
    contactName: "Michelle Park",
    contactEmail: "michelle@example.com",
    jobDescription: "Blocked drain clearance",
    amountAud: 350,
    sentAt: new Date(Date.now() - 2 * 86400000).toISOString(),
    status: "sent",
    source: "email",
  },
  {
    id: "qt-004",
    quoteNumber: "Q-1045",
    contactName: "David Lopez",
    contactEmail: "david@example.com",
    jobDescription: "Kitchen renovation plumbing",
    amountAud: 4500,
    sentAt: new Date(Date.now() - 15 * 86400000).toISOString(),
    status: "sent",
    source: "xero",
  },
  {
    id: "qt-005",
    quoteNumber: "Q-1046",
    contactName: "Emma Wilson",
    contactEmail: "emma@example.com",
    jobDescription: "Leak detection",
    amountAud: 290,
    sentAt: new Date(Date.now() - 4 * 86400000).toISOString(),
    status: "sent",
    lastCustomerReplyAt: new Date(Date.now() - 3 * 86400000).toISOString(),
    source: "email",
  },
  {
    id: "qt-006",
    quoteNumber: "Q-1047",
    contactName: "Tom Harris",
    contactEmail: "tom@example.com",
    jobDescription: "Gas bayonet install",
    amountAud: 680,
    sentAt: new Date(Date.now() - 20 * 86400000).toISOString(),
    status: "won",
    source: "email",
  },
];

function store() {
  if (!globalStore.__qcStore) {
    const quotes = new Map<string, Quote>();
    for (const q of DEMO_QUOTES) {
      const enriched = enrichQuote(q);
      quotes.set(enriched.id, enriched);
    }
    globalStore.__qcStore = {
      settings: {
        businessName: "RapidFlow Plumbing",
        senderName: "Alex",
        followUpCadenceDays: [3, 7, 14],
      },
      quotes,
      sequences: new Map(),
      drafts: new Map(),
    };
  }
  return globalStore.__qcStore;
}

export function getSettings(): BusinessSettings {
  return store().settings;
}

export function listQuotes(): Quote[] {
  return [...store().quotes.values()]
    .map((q) => enrichQuote(q))
    .sort((a, b) => b.daysSinceSent - a.daysSinceSent);
}

export function getQuote(id: string): Quote | undefined {
  const q = store().quotes.get(id);
  return q ? enrichQuote(q) : undefined;
}

export function listStaleQuotes(): Quote[] {
  return detectStaleQuotes(listQuotes());
}

export function listDrafts(): FollowUpDraft[] {
  return [...store().drafts.values()].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function getOrCreateSequence(quoteId: string): FollowUpSequence {
  const existing = [...store().sequences.values()].find((s) => s.quoteId === quoteId);
  if (existing) return existing;

  const quote = getQuote(quoteId);
  if (!quote) throw new Error("Quote not found");

  const stage = stageForDays(quote.daysSinceSent, store().settings.followUpCadenceDays);
  const seq: FollowUpSequence = {
    id: randomUUID(),
    quoteId,
    stage,
    status: "pending_approval",
    nextActionAt: nextActionDate(quote.sentAt, stage, store().settings.followUpCadenceDays),
    followUpsSent: 0,
    updatedAt: new Date().toISOString(),
  };
  store().sequences.set(seq.id, seq);
  return seq;
}

export function generateDraft(quoteId: string): FollowUpDraft | null {
  const quote = getQuote(quoteId);
  if (!quote || !needsFollowUp(quote)) return null;

  const seq = getOrCreateSequence(quoteId);
  if (!isDueForFollowUp(quote.daysSinceSent, seq.followUpsSent, store().settings.followUpCadenceDays)) {
    return null;
  }

  const existing = [...store().drafts.values()].find(
    (d) => d.quoteId === quoteId && d.stage === seq.stage && d.status === "draft",
  );
  if (existing) return existing;

  const draft = draftFollowUp(
    quote,
    seq.stage,
    store().settings.businessName,
    store().settings.senderName,
    seq.id,
  );
  store().drafts.set(draft.id, draft);
  return draft;
}

export function updateDraftBody(draftId: string, subject: string, body: string): FollowUpDraft | null {
  const draft = store().drafts.get(draftId);
  if (!draft) return null;
  draft.subject = subject;
  draft.body = body;
  return draft;
}

export function approveAndSend(draftId: string): { draft: FollowUpDraft; result: ReturnType<typeof sendFollowUpEmail> } | null {
  const draft = store().drafts.get(draftId);
  const quote = draft ? getQuote(draft.quoteId) : undefined;
  const seq = draft ? store().sequences.get(draft.sequenceId) : undefined;
  if (!draft || !quote || !seq) return null;

  const result = sendFollowUpEmail(quote.contactEmail, draft.subject, draft.body);
  if (result.success) {
    draft.status = "sent";
    seq.followUpsSent += 1;
    seq.status = "sent";
    seq.updatedAt = new Date().toISOString();
  }
  return { draft, result };
}

export function rejectDraft(draftId: string): boolean {
  const draft = store().drafts.get(draftId);
  if (!draft) return false;
  draft.status = "rejected";
  return true;
}

export function pendingCount(): number {
  return listDrafts().filter((d) => d.status === "draft").length;
}

export function isMockMode(): boolean {
  return !process.env.GMAIL_CLIENT_ID && !process.env.MICROSOFT_GRAPH_TOKEN;
}

export function resetStore(): void {
  globalStore.__qcStore = undefined;
}
