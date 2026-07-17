export type CallState =
  | "GREETING"
  | "JOB_TYPE"
  | "SUBURB"
  | "URGENCY"
  | "EMERGENCY_DETAILS"
  | "CALLBACK_SLOT"
  | "SUMMARY"
  | "COMPLETE";

export type Urgency = "routine" | "soon" | "emergency";

export type CallOutcome =
  | "in_progress"
  | "callback_booked"
  | "emergency_escalated"
  | "voicemail"
  | "abandoned";

export interface EmergencyCriteria {
  keywords: string[];
  escalateUrgencies: Urgency[];
}

export interface BusinessProfile {
  id: string;
  name: string;
  trade: string;
  afterHoursNumber: string;
  onCallPhone: string;
  hoursStart: string;
  hoursEnd: string;
  emergency: EmergencyCriteria;
}

export interface VoiceSession {
  id: string;
  phone: string;
  state: CallState;
  jobType?: string;
  suburb?: string;
  urgency?: Urgency;
  emergencyDetails?: string;
  callbackSlot?: string;
  transcript: { role: "agent" | "caller"; text: string; at: string }[];
  outcome: CallOutcome;
  escalated: boolean;
  startedAt: string;
  updatedAt: string;
}

export interface CallRecord {
  id: string;
  sessionId: string;
  phone: string;
  summary: string;
  outcome: CallOutcome;
  escalated: boolean;
  callbackSlot?: string;
  recordingPurgedAt?: string;
  createdAt: string;
}
