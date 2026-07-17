export type ChaseStage = 0 | 1 | 2 | 3;

export type ReminderTone = "friendly" | "firm" | "final";

export type ChaseStatus =
  | "pending_approval"
  | "approved"
  | "sent"
  | "paused"
  | "paid"
  | "disputed"
  | "opted_out";

export type ReplyIntent =
  | "paid"
  | "dispute"
  | "promise_to_pay"
  | "question"
  | "opt_out"
  | "unknown";

export interface Invoice {
  id: string;
  invoiceNumber: string;
  contactName: string;
  contactEmail: string;
  amountDue: number;
  currency: string;
  dueDate: string;
  daysOverdue: number;
  xeroInvoiceId?: string;
}

export interface ChaseSequence {
  id: string;
  invoiceId: string;
  stage: ChaseStage;
  status: ChaseStatus;
  nextActionAt: string;
  lastReminderAt?: string;
  remindersSent: number;
  updatedAt: string;
}

export interface ReminderDraft {
  id: string;
  sequenceId: string;
  invoiceId: string;
  stage: ChaseStage;
  tone: ReminderTone;
  channel: "email" | "sms";
  subject: string;
  body: string;
  status: "draft" | "approved" | "sent" | "rejected";
  createdAt: string;
}

export interface ReplyClassification {
  intent: ReplyIntent;
  confidence: "high" | "medium" | "low";
  summary: string;
  suggestedAction: string;
}

export interface BusinessSettings {
  businessName: string;
  senderName: string;
  paymentTermsDays: number;
}
