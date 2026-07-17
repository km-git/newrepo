import type { ReplyClassification, ReplyIntent } from "./types";

const PATTERNS: { intent: ReplyIntent; regex: RegExp; action: string }[] = [
  {
    intent: "opt_out",
    regex: /\b(stop|unsubscribe|remove me|don't email)\b/i,
    action: "Stop all reminders for this contact; mark sequence opted out.",
  },
  {
    intent: "paid",
    regex: /\b(paid|payment sent|transferred|cleared|eft done|already paid)\b/i,
    action: "Verify in Xero; if confirmed, mark invoice paid and stop sequence.",
  },
  {
    intent: "dispute",
    regex: /\b(dispute|incorrect|wrong amount|not mine|never received|query)\b/i,
    action: "Pause sequence; notify owner for manual review.",
  },
  {
    intent: "promise_to_pay",
    regex: /\b(pay (on |this )?friday|next week|will pay|payment (on|by)|eft (on|by))\b/i,
    action: "Log promise date; schedule follow-up after promised date.",
  },
  {
    intent: "question",
    regex: /\b(how much|which invoice|bank details|bsb|account number|copy)\b/i,
    action: "Draft helpful reply with invoice details for owner approval.",
  },
];

export function classifyReply(text: string): ReplyClassification {
  const trimmed = text.trim();
  if (!trimmed) {
    return {
      intent: "unknown",
      confidence: "low",
      summary: "Empty reply",
      suggestedAction: "Ask owner to follow up manually.",
    };
  }

  for (const p of PATTERNS) {
    if (p.regex.test(trimmed)) {
      return {
        intent: p.intent,
        confidence: "high",
        summary: `Detected: ${p.intent.replace(/_/g, " ")}`,
        suggestedAction: p.action,
      };
    }
  }

  return {
    intent: "unknown",
    confidence: "low",
    summary: "Could not classify reply",
    suggestedAction: "Route to owner inbox for manual response.",
  };
}

export function applyReplyToStatus(intent: ReplyIntent): "paid" | "disputed" | "paused" | "opted_out" | null {
  switch (intent) {
    case "paid":
      return "paid";
    case "dispute":
      return "disputed";
    case "opt_out":
      return "opted_out";
    case "promise_to_pay":
      return "paused";
    default:
      return null;
  }
}
