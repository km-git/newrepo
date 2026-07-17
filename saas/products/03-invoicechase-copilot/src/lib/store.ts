import { randomUUID } from "crypto";
import type {
  BusinessSettings,
  ChaseSequence,
  ChaseStatus,
  Invoice,
  ReminderDraft,
} from "./types";
import { draftReminder } from "./reminder-drafter";
import { stageForDaysOverdue } from "./escalation-ladder";
import { applyReplyToStatus, classifyReply } from "./reply-classifier";

const globalStore = globalThis as typeof globalThis & {
  __iccStore?: {
    invoices: Map<string, Invoice>;
    sequences: Map<string, ChaseSequence>;
    drafts: Map<string, ReminderDraft>;
    settings: BusinessSettings;
  };
};

function store() {
  if (!globalStore.__iccStore) {
    const demoInvoices: Invoice[] = [
      {
        id: "inv-001",
        invoiceNumber: "INV-1042",
        contactName: "Smith Renovations",
        contactEmail: "accounts@smithreno.com.au",
        amountDue: 4850.0,
        currency: "AUD",
        dueDate: "2026-06-01",
        daysOverdue: 46,
        xeroInvoiceId: "xero-abc-1042",
      },
      {
        id: "inv-002",
        invoiceNumber: "INV-1055",
        contactName: "Coastal Plumbing",
        contactEmail: "admin@coastalplumb.com.au",
        amountDue: 1275.5,
        currency: "AUD",
        dueDate: "2026-06-20",
        daysOverdue: 27,
        xeroInvoiceId: "xero-abc-1055",
      },
      {
        id: "inv-003",
        invoiceNumber: "INV-1061",
        contactName: "Metro Fitouts",
        contactEmail: "ap@metrofitouts.com.au",
        amountDue: 9200.0,
        currency: "AUD",
        dueDate: "2026-07-01",
        daysOverdue: 16,
        xeroInvoiceId: "xero-abc-1061",
      },
    ];

    const invoices = new Map(demoInvoices.map((i) => [i.id, i]));
    const sequences = new Map<string, ChaseSequence>();
    const drafts = new Map<string, ReminderDraft>();

    for (const inv of demoInvoices) {
      const seq = createSequenceForInvoice(inv);
      sequences.set(seq.id, seq);
    }

    globalStore.__iccStore = {
      invoices,
      sequences,
      drafts,
      settings: {
        businessName: "Demo Tradie Services Pty Ltd",
        senderName: "Accounts Team",
        paymentTermsDays: 14,
      },
    };
  }
  return globalStore.__iccStore;
}

function createSequenceForInvoice(invoice: Invoice): ChaseSequence {
  const stage = stageForDaysOverdue(invoice.daysOverdue);
  return {
    id: randomUUID(),
    invoiceId: invoice.id,
    stage: stage > 0 ? stage : 0,
    status: "pending_approval",
    nextActionAt: new Date().toISOString(),
    remindersSent: 0,
    updatedAt: new Date().toISOString(),
  };
}

export function getSettings(): BusinessSettings {
  return store().settings;
}

export function listInvoices(): Invoice[] {
  return [...store().invoices.values()].sort(
    (a, b) => b.daysOverdue - a.daysOverdue,
  );
}

export function getInvoice(id: string): Invoice | undefined {
  return store().invoices.get(id);
}

export function getSequenceForInvoice(invoiceId: string): ChaseSequence | undefined {
  for (const s of store().sequences.values()) {
    if (s.invoiceId === invoiceId) return s;
  }
  return undefined;
}

export function listPendingDrafts(): ReminderDraft[] {
  return [...store().drafts.values()]
    .filter((d) => d.status === "draft")
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}

export function listAllDrafts(): ReminderDraft[] {
  return [...store().drafts.values()].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function generateDraftForInvoice(invoiceId: string): ReminderDraft | null {
  const invoice = store().invoices.get(invoiceId);
  const sequence = getSequenceForInvoice(invoiceId);
  if (!invoice || !sequence) return null;

  if (["paid", "disputed", "opted_out"].includes(sequence.status)) {
    return null;
  }

  const targetStage = stageForDaysOverdue(invoice.daysOverdue);
  if (targetStage === 0) return null;

  const draft = draftReminder(
    invoice,
    targetStage,
    store().settings,
    sequence.id,
  );
  store().drafts.set(draft.id, draft);
  return draft;
}

export function approveDraft(draftId: string): ReminderDraft | null {
  const draft = store().drafts.get(draftId);
  if (!draft || draft.status !== "draft") return null;

  draft.status = "approved";
  const sequence = [...store().sequences.values()].find(
    (s) => s.id === draft.sequenceId,
  );
  if (sequence) {
    sequence.status = "sent";
    sequence.stage = draft.stage;
    sequence.remindersSent += 1;
    sequence.lastReminderAt = new Date().toISOString();
    sequence.updatedAt = new Date().toISOString();
  }

  draft.status = "sent";
  return draft;
}

export function rejectDraft(draftId: string): boolean {
  const draft = store().drafts.get(draftId);
  if (!draft) return false;
  draft.status = "rejected";
  return true;
}

export function handleDebtorReply(
  invoiceId: string,
  replyText: string,
): { classification: ReturnType<typeof classifyReply>; sequence?: ChaseSequence } {
  const sequence = getSequenceForInvoice(invoiceId);
  const classification = classifyReply(replyText);
  const newStatus = applyReplyToStatus(classification.intent);

  if (sequence && newStatus) {
    sequence.status = newStatus as ChaseStatus;
    sequence.updatedAt = new Date().toISOString();
    if (newStatus === "paid") {
      const inv = store().invoices.get(invoiceId);
      if (inv) inv.daysOverdue = 0;
    }
  }

  return { classification, sequence };
}

export function advanceOverdueInvoices(): ReminderDraft[] {
  const generated: ReminderDraft[] = [];
  for (const inv of store().invoices.values()) {
    if (inv.daysOverdue > 0) {
      const draft = generateDraftForInvoice(inv.id);
      if (draft) generated.push(draft);
    }
  }
  return generated;
}

export function resetStore(): void {
  globalStore.__iccStore = undefined;
}

export function isMockMode(): boolean {
  return !process.env.XERO_CLIENT_ID || !process.env.XERO_CLIENT_SECRET;
}
