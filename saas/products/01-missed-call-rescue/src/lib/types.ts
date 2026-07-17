export type Urgency = "routine" | "soon" | "emergency";

export type ConversationState =
  | "AWAITING_JOB_TYPE"
  | "AWAITING_SUBURB"
  | "AWAITING_URGENCY"
  | "AWAITING_NOTES"
  | "COMPLETE"
  | "OPTED_OUT";

export type LeadStatus = "qualifying" | "ready" | "called" | "won" | "lost" | "opted_out";

export interface LeadCard {
  id: string;
  phone: string;
  trade: string;
  jobType: string;
  suburb: string;
  urgency: Urgency;
  notes: string;
  status: LeadStatus;
  createdAt: string;
  updatedAt: string;
  summary: string;
}

export interface SmsSession {
  id: string;
  phone: string;
  trade: string;
  state: ConversationState;
  jobType?: string;
  suburb?: string;
  urgency?: Urgency;
  notes: string[];
  optedOut: boolean;
  leadId?: string;
  updatedAt: string;
}

export interface BusinessProfile {
  id: string;
  name: string;
  trade: string;
  twilioNumber: string;
  ownerPhone: string;
}
