/** Shared portfolio types — minimal PII, job metadata only. */

export type Urgency = "routine" | "soon" | "emergency";

export type LeadStatus = "qualifying" | "ready" | "called" | "won" | "lost" | "opted_out";

export interface LeadCard {
  id: string;
  phone: string;
  trade: string;
  jobType: string;
  suburb: string;
  urgency: Urgency;
  notes: string;
  photoUrls: string[];
  status: LeadStatus;
  createdAt: string;
  updatedAt: string;
  summary: string;
}

export interface SmsSession {
  id: string;
  phone: string;
  trade: string;
  state: string;
  jobType?: string;
  suburb?: string;
  urgency?: Urgency;
  notes: string[];
  optedOut: boolean;
  leadId?: string;
  updatedAt: string;
}
