export type TradeScript = {
  trade: string;
  greeting: string;
  emergencyKeywords: string[];
  jobExamples: string[];
};

export const TRADE_SCRIPTS: Record<string, TradeScript> = {
  plumber: {
    trade: "plumber",
    greeting:
      "Sorry we missed your call — {business}. What plumbing issue can we help with? (e.g. blocked drain, hot water, leak)",
    emergencyKeywords: [
      "burst",
      "flooding",
      "flood",
      "gas",
      "no water",
      "sewage",
      "overflow",
    ],
    jobExamples: ["blocked drain", "hot water", "tap leak", "toilet"],
  },
  electrician: {
    trade: "electrician",
    greeting:
      "Sorry we missed your call — {business}. What's the electrical issue? (e.g. power out, safety switch, install)",
    emergencyKeywords: [
      "no power",
      "spark",
      "burning",
      "shock",
      "smoke",
      "fire",
    ],
    jobExamples: ["power out", "safety switch", "lights", "install"],
  },
  general: {
    trade: "general",
    greeting:
      "Sorry we missed your call — {business}. What do you need help with?",
    emergencyKeywords: ["emergency", "urgent", "danger", "injury"],
    jobExamples: ["repair", "quote", "service"],
  },
};

export function getTradeScript(trade: string): TradeScript {
  return TRADE_SCRIPTS[trade] ?? TRADE_SCRIPTS.general;
}
