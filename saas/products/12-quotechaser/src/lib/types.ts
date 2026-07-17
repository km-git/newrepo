export type QuoteStatus = "sent" | "viewed" | "replied" | "won" | "lost" | "stale";

export type FollowUpStage = 0 | 1 | 2 | 3;

export type FollowUpTone = "gentle" | "friendly" | "firm";

export type FollowUpStatus =
  | "pending_approval"
  | "approved"
  | "sent"
  | "rejected"
  | "paused";

export type ThreadState = "awaiting_reply" | "customer_replied" | "closed";

export interface Quote {
  id: string;
  quoteNumber: string;
  contactName: string;
  contactEmail: string;
  jobDescription: string;
  amountAud: number;
  sentAt: string;
  daysSinceSent: number;
  status: QuoteStatus;
  threadState: ThreadState;
  lastCustomerReplyAt?: string;
  source: "email" | "xero";
}

export interface FollowUpSequence {
  id: string;
  quoteId: string;
  stage: FollowUpStage;
  status: FollowUpStatus;
  nextActionAt: string;
  followUpsSent: number;
  updatedAt: string;
}

export interface FollowUpDraft {
  id: string;
  sequenceId: string;
  quoteId: string;
  stage: FollowUpStage;
  tone: FollowUpTone;
  subject: string;
  body: string;
  status: "draft" | "approved" | "sent" | "rejected";
  createdAt: string;
}

export interface BusinessSettings {
  businessName: string;
  senderName: string;
  followUpCadenceDays: number[];
}
