import type { BusinessProfile, CallState } from "./types";

export const FLOW_VERSION = "1.0.0";

const PROMPTS: Record<CallState, (biz: BusinessProfile) => string> = {
  GREETING: (biz) =>
    `Thanks for calling ${biz.name}. We're currently closed, but I can help capture your job details and arrange a callback or escalate genuine emergencies. What type of job do you need help with?`,
  JOB_TYPE: () => "Got it. Which suburb are you in?",
  SUBURB: () =>
    "Thanks. Is this an emergency right now — like flooding, no hot water, or a safety issue — or can it wait until morning?",
  URGENCY: () => "Can you briefly describe what's happening?",
  EMERGENCY_DETAILS: () =>
    "I've flagged this for our on-call technician. They'll call you back shortly. Is there anything else I should note?",
  CALLBACK_SLOT: () =>
    "I can book a callback for first thing tomorrow between 7 and 9 am, or between 9 and 11 am. Which works better?",
  SUMMARY: () =>
    "Perfect. I've captured everything and will send a summary. Thanks for calling — stay safe.",
  COMPLETE: () => "Goodbye.",
};

export function getAgentPrompt(state: CallState, biz: BusinessProfile): string {
  return PROMPTS[state](biz);
}

export function parseUrgency(text: string): "routine" | "soon" | "emergency" | null {
  const lower = text.toLowerCase();
  if (/\b(not urgent|no rush|can wait|non[- ]?urgent)\b/.test(lower)) {
    return "routine";
  }
  if (/\b(emergency|urgent|flooding|burst|gas leak|no power|locked out|sparking)\b/.test(lower)) {
    return "emergency";
  }
  if (/\b(soon|today|asap|this evening|tonight)\b/.test(lower)) {
    return "soon";
  }
  if (/\b(routine|morning|tomorrow|next week)\b/.test(lower)) {
    return "routine";
  }
  return null;
}

export function parseCallbackSlot(text: string): string | null {
  const lower = text.toLowerCase();
  if (/7|first|early|morning/.test(lower) && !/9.*11/.test(lower)) {
    return "Tomorrow 7–9 am";
  }
  if (/9|11|later/.test(lower)) {
    return "Tomorrow 9–11 am";
  }
  return null;
}
