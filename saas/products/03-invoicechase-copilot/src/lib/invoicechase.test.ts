import { describe, it, expect, beforeEach } from "vitest";
import { stageForDaysOverdue, nextStage, toneForStage } from "./escalation-ladder";
import { classifyReply, applyReplyToStatus } from "./reply-classifier";
import { draftReminder } from "./reminder-drafter";
import {
  resetStore,
  generateDraftForInvoice,
  approveDraft,
  handleDebtorReply,
  listInvoices,
} from "./store";
import type { Invoice } from "./types";

const sampleInvoice: Invoice = {
  id: "test-inv",
  invoiceNumber: "INV-999",
  contactName: "Test Co",
  contactEmail: "test@example.com",
  amountDue: 1000,
  currency: "AUD",
  dueDate: "2026-05-01",
  daysOverdue: 30,
};

describe("escalation-ladder", () => {
  it("maps days overdue to correct stage", () => {
    expect(stageForDaysOverdue(5)).toBe(0);
    expect(stageForDaysOverdue(10)).toBe(1);
    expect(stageForDaysOverdue(25)).toBe(2);
    expect(stageForDaysOverdue(40)).toBe(3);
  });

  it("advances stages", () => {
    expect(nextStage(1)).toBe(2);
    expect(nextStage(3)).toBeNull();
    expect(toneForStage(2)).toBe("firm");
  });
});

describe("reply-classifier", () => {
  it("classifies paid replies", () => {
    const r = classifyReply("Thanks, payment sent yesterday via EFT");
    expect(r.intent).toBe("paid");
    expect(applyReplyToStatus(r.intent)).toBe("paid");
  });

  it("classifies disputes", () => {
    const r = classifyReply("This amount is incorrect, we dispute the invoice");
    expect(r.intent).toBe("dispute");
  });

  it("classifies promise to pay", () => {
    const r = classifyReply("Will pay on Friday when payroll clears");
    expect(r.intent).toBe("promise_to_pay");
    expect(applyReplyToStatus(r.intent)).toBe("paused");
  });

  it("classifies opt-out", () => {
    const r = classifyReply("STOP emailing me");
    expect(r.intent).toBe("opt_out");
  });
});

describe("reminder-drafter", () => {
  it("drafts tone-appropriate reminder", () => {
    const draft = draftReminder(sampleInvoice, 2, {
      businessName: "Ace Trades",
      senderName: "Sam",
      paymentTermsDays: 14,
    }, "seq-1");
    expect(draft.tone).toBe("firm");
    expect(draft.body).toContain("INV-999");
    expect(draft.body).toContain("30 days overdue");
    expect(draft.status).toBe("draft");
  });
});

describe("store workflow", () => {
  beforeEach(() => resetStore());

  it("generates draft for overdue demo invoice", () => {
    const invoices = listInvoices();
    const overdue = invoices.find((i) => i.daysOverdue > 7);
    expect(overdue).toBeDefined();
    const draft = generateDraftForInvoice(overdue!.id);
    expect(draft).toBeDefined();
    expect(draft!.status).toBe("draft");
  });

  it("requires approval before marking sent", () => {
    const invoices = listInvoices();
    const inv = invoices[0];
    const draft = generateDraftForInvoice(inv.id);
    expect(draft).toBeDefined();
    const approved = approveDraft(draft!.id);
    expect(approved!.status).toBe("sent");
  });

  it("pauses sequence on debtor reply", () => {
    const invoices = listInvoices();
    const inv = invoices[0];
    const { classification, sequence } = handleDebtorReply(
      inv.id,
      "We will pay next week on Thursday",
    );
    expect(classification.intent).toBe("promise_to_pay");
    expect(sequence?.status).toBe("paused");
  });
});
