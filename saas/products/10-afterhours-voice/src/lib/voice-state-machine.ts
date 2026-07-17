import { randomUUID } from "crypto";
import type { BusinessProfile, CallRecord, VoiceSession } from "./types";
import { getAgentPrompt, parseCallbackSlot, parseUrgency } from "./call-flow";
import { escalationMessage, isEmergency } from "./emergency-triage";
import { sendEscalationSms } from "./telephony-adapter";

function now() {
  return new Date().toISOString();
}

function addTranscript(
  session: VoiceSession,
  role: "agent" | "caller",
  text: string,
): void {
  session.transcript.push({ role, text, at: now() });
}

export function startSession(phone: string, biz: BusinessProfile): VoiceSession {
  const greeting = getAgentPrompt("GREETING", biz);
  const session: VoiceSession = {
    id: randomUUID(),
    phone,
    state: "JOB_TYPE",
    transcript: [],
    outcome: "in_progress",
    escalated: false,
    startedAt: now(),
    updatedAt: now(),
  };
  addTranscript(session, "agent", greeting);
  return session;
}

export interface TurnResult {
  session: VoiceSession;
  reply: string;
  escalated: boolean;
  escalationSms?: string;
  callRecord?: CallRecord;
}

export function processUtterance(
  session: VoiceSession,
  utterance: string,
  biz: BusinessProfile,
): TurnResult {
  addTranscript(session, "caller", utterance);
  let reply = "";
  let escalated = false;
  let escalationSms: string | undefined;
  let callRecord: CallRecord | undefined;

  switch (session.state) {
    case "JOB_TYPE":
      session.jobType = utterance.trim();
      session.state = "SUBURB";
      reply = getAgentPrompt("JOB_TYPE", biz);
      break;

    case "SUBURB":
      session.suburb = utterance.trim();
      session.state = "URGENCY";
      reply = getAgentPrompt("SUBURB", biz);
      break;

    case "URGENCY": {
      const urgency = parseUrgency(utterance) ?? "routine";
      session.urgency = urgency;
      if (urgency === "emergency" || isEmergency(urgency, utterance, biz.emergency)) {
        session.state = "EMERGENCY_DETAILS";
        reply = getAgentPrompt("URGENCY", biz);
      } else {
        session.state = "CALLBACK_SLOT";
        reply =
          urgency === "soon"
            ? "Understood — sounds like you need help soon. I can book a priority callback this evening or first thing tomorrow. Which do you prefer?"
            : getAgentPrompt("CALLBACK_SLOT", biz);
      }
      break;
    }

    case "EMERGENCY_DETAILS":
      session.emergencyDetails = utterance.trim();
      session.escalated = true;
      session.outcome = "emergency_escalated";
      session.state = "SUMMARY";
      escalated = true;
      escalationSms = escalationMessage(
        biz.name,
        session.suburb ?? "unknown suburb",
        session.jobType ?? "job",
        session.emergencyDetails,
      );
      sendEscalationSms(biz, escalationSms);
      reply = getAgentPrompt("EMERGENCY_DETAILS", biz);
      break;

    case "CALLBACK_SLOT": {
      const slot = parseCallbackSlot(utterance) ?? "Tomorrow 7–9 am";
      session.callbackSlot = slot;
      session.outcome = "callback_booked";
      session.state = "SUMMARY";
      reply = `Great — I've booked a callback for ${slot}. ${getAgentPrompt("SUMMARY", biz)}`;
      break;
    }

    case "SUMMARY":
      session.state = "COMPLETE";
      session.outcome =
        session.outcome === "in_progress" ? "callback_booked" : session.outcome;
      reply = getAgentPrompt("COMPLETE", biz);
      callRecord = buildCallRecord(session);
      break;

    default:
      reply = "Thanks for calling. Goodbye.";
      session.state = "COMPLETE";
      callRecord = buildCallRecord(session);
  }

  addTranscript(session, "agent", reply);
  session.updatedAt = now();
  return { session, reply, escalated, escalationSms, callRecord };
}

function buildCallRecord(session: VoiceSession): CallRecord {
  return {
    id: randomUUID(),
    sessionId: session.id,
    phone: session.phone,
    summary: [
      session.jobType,
      session.suburb,
      session.urgency,
      session.emergencyDetails,
      session.callbackSlot,
    ]
      .filter(Boolean)
      .join(" · "),
    outcome: session.outcome === "in_progress" ? "callback_booked" : session.outcome,
    escalated: session.escalated,
    callbackSlot: session.callbackSlot,
    createdAt: now(),
  };
}

export function summarizeCall(session: VoiceSession): string {
  const lines = session.transcript.map((t) => `${t.role}: ${t.text}`);
  return lines.join("\n");
}
