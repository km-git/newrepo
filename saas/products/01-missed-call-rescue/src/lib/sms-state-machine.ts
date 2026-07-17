import { randomUUID } from "crypto";
import type { LeadCard, SmsSession, Urgency } from "./types";
import { getTradeScript } from "./trade-scripts";
import { createSession, getSessionByPhone, saveLead, saveSession } from "./store";

const OPT_OUT_KEYWORDS = ["stop", "unsubscribe", "opt out", "optout", "cancel sms"];
const EMERGENCY_GLOBAL = /emergency|urgent|asap|flooding|gas leak|no power|burst pipe/i;

export interface SmsTurnResult {
  reply: string;
  session: SmsSession;
  lead?: LeadCard;
  notifyOwner?: boolean;
}

export function isOptOut(text: string): boolean {
  const t = text.trim().toLowerCase();
  return OPT_OUT_KEYWORDS.some((k) => t === k || t.startsWith(k + " "));
}

export function detectUrgency(text: string, trade: string): Urgency {
  const script = getTradeScript(trade);
  const lower = text.toLowerCase();
  if (
    EMERGENCY_GLOBAL.test(text) ||
    script.emergencyKeywords.some((k) => lower.includes(k))
  ) {
    return "emergency";
  }
  if (/today|this week|soon|asap/i.test(text)) return "soon";
  return "routine";
}

export function greetingForTrade(trade: string, businessName: string): string {
  const script = getTradeScript(trade);
  return script.greeting.replace("{business}", businessName);
}

export function handleMissedCall(
  phone: string,
  trade: string,
  businessName: string,
): { message: string; session: SmsSession } {
  let session = getSessionByPhone(phone);
  if (!session) {
    session = createSession(phone, trade);
  }
  const message = greetingForTrade(trade, businessName);
  return { message, session };
}

export function handleInboundSms(
  phone: string,
  body: string,
  trade: string,
  businessName: string,
): SmsTurnResult {
  if (isOptOut(body)) {
    const session = getSessionByPhone(phone) ?? createSession(phone, trade);
    session.state = "OPTED_OUT";
    session.optedOut = true;
    session.updatedAt = new Date().toISOString();
    saveSession(session);
    return {
      reply: "You've been unsubscribed. Reply START to opt back in.",
      session,
    };
  }

  let session = getSessionByPhone(phone);
  if (!session) {
    session = createSession(phone, trade);
    return {
      reply: greetingForTrade(trade, businessName),
      session,
    };
  }

  const text = body.trim();
  if (!text) {
    return { reply: "Please send a short reply so we can help.", session };
  }

  switch (session.state) {
    case "AWAITING_JOB_TYPE": {
      session.jobType = text;
      session.state = "AWAITING_SUBURB";
      session.updatedAt = new Date().toISOString();
      saveSession(session);
      const urgency = detectUrgency(text, trade);
      if (urgency === "emergency") {
        session.urgency = "emergency";
      }
      return {
        reply: "Thanks! What suburb are you in?",
        session,
        notifyOwner: urgency === "emergency",
      };
    }
    case "AWAITING_SUBURB": {
      session.suburb = text;
      session.state = "AWAITING_URGENCY";
      session.updatedAt = new Date().toISOString();
      saveSession(session);
      return {
        reply:
          "Got it. How urgent is this? Reply: routine / soon / emergency",
        session,
      };
    }
    case "AWAITING_URGENCY": {
      session.urgency = parseUrgency(text, trade);
      session.state = "AWAITING_NOTES";
      session.updatedAt = new Date().toISOString();
      saveSession(session);
      return {
        reply:
          "Any extra details? (access, photos via MMS, or reply skip)",
        session,
        notifyOwner: session.urgency === "emergency",
      };
    }
    case "AWAITING_NOTES": {
      if (text.toLowerCase() !== "skip") {
        session.notes.push(text);
      }
      session.state = "COMPLETE";
      session.updatedAt = new Date().toISOString();
      saveSession(session);

      const lead = buildLeadCard(session);
      session.leadId = lead.id;
      saveSession(session);
      saveLead(lead);

      return {
        reply: `Thanks ${session.suburb ? "—" : ""}! We've got your details. ${
          session.urgency === "emergency"
            ? "Someone will call you shortly."
            : "We'll call you back as soon as we're free."
        }`,
        session,
        lead,
        notifyOwner: session.urgency === "emergency",
      };
    }
    default:
      return {
        reply: "Your request is already logged. We'll be in touch soon.",
        session,
      };
  }
}

function parseUrgency(text: string, trade: string): Urgency {
  const lower = text.toLowerCase();
  if (lower.includes("emergency") || detectUrgency(text, trade) === "emergency") {
    return "emergency";
  }
  if (lower.includes("soon") || lower.includes("today")) return "soon";
  return "routine";
}

export function buildLeadCard(session: SmsSession): LeadCard {
  const now = new Date().toISOString();
  const notes = session.notes.join("; ");
  const summary = [
    session.jobType,
    session.suburb,
    session.urgency ?? "routine",
    notes || "No extra notes",
  ]
    .filter(Boolean)
    .join(" · ");

  return {
    id: randomUUID(),
    phone: session.phone,
    trade: session.trade,
    jobType: session.jobType ?? "Unknown",
    suburb: session.suburb ?? "Unknown",
    urgency: session.urgency ?? "routine",
    notes,
    status: "ready",
    createdAt: now,
    updatedAt: now,
    summary,
  };
}
