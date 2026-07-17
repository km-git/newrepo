import type { JobCardData } from "./types";

const PHONE_RE = /(?:\+?61|0)[\s-]?(?:4\d{2}|[2378])\s?\d{3}\s?\d{3,4}|\b0\d{2}\s?\d{4}\s?\d{4}\b/;
const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
const ADDRESS_RE =
  /\d+\s+[\w\s]+(?:street|st|road|rd|avenue|ave|drive|dr|court|ct|place|pl|crescent|cres|way|parade|pde)\b[^,\n]*/i;
const SUBURB_RE =
  /\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:NSW|VIC|QLD|SA|WA|TAS|NT|ACT)?\s*\d{4}\b/;

const JOB_KEYWORDS: Record<string, string[]> = {
  plumbing: ["blocked", "drain", "leak", "toilet", "hot water", "tap", "pipe", "plumb"],
  electrical: ["power", "light", "switch", "outlet", "safety switch", "electric", "wiring"],
  building: ["renovation", "deck", "fence", "repair", "build", "extension"],
  general: ["quote", "service", "repair", "fix", "install"],
};

const URGENCY_PATTERNS = {
  emergency: /emergency|urgent|asap|flooding|no power|burst|danger/i,
  soon: /today|tomorrow|this week|as soon as/i,
};

export interface ExtractionResult {
  data: Partial<JobCardData>;
  ambiguities: string[];
  confidence: "high" | "medium" | "low";
}

export function extractFromEmail(
  subject: string,
  body: string,
  from: string,
): ExtractionResult {
  const text = `${subject}\n${body}`;
  const ambiguities: string[] = [];

  const phoneMatch = text.match(PHONE_RE);
  const emailMatch = text.match(EMAIL_RE) ?? [from.match(EMAIL_RE)?.[0]].filter(Boolean);
  const addressMatch = text.match(ADDRESS_RE);
  const suburbMatch = text.match(SUBURB_RE);

  const customerName = extractName(text, from);
  if (!customerName) ambiguities.push("Could not determine customer name");

  const jobType = detectJobType(text);
  if (jobType === "general enquiry") ambiguities.push("Job type unclear — please confirm");

  const siteAddress = addressMatch?.[0]?.trim() ?? "";
  if (!siteAddress) ambiguities.push("No street address found — add manually");

  const suburb = suburbMatch?.[1]?.trim();
  if (!suburb) ambiguities.push("Suburb not detected");

  const urgency = detectUrgency(text);
  const preferredDate = extractPreferredDate(text);

  const data: Partial<JobCardData> = {
    customerName: customerName ?? "Unknown",
    customerPhone: phoneMatch?.[0]?.replace(/\s/g, ""),
    customerEmail: emailMatch[0] as string | undefined,
    siteAddress: siteAddress || "Address TBC",
    suburb,
    jobType,
    urgency,
    description: cleanDescription(body),
    preferredDate,
    photoUrls: [],
  };

  const filled = [
    data.customerName && data.customerName !== "Unknown",
    data.siteAddress && data.siteAddress !== "Address TBC",
    data.jobType,
    data.description,
  ].filter(Boolean).length;

  const confidence =
    filled >= 4 && ambiguities.length === 0
      ? "high"
      : filled >= 2
        ? "medium"
        : "low";

  return { data, ambiguities, confidence };
}

function extractName(text: string, from: string): string | undefined {
  const fromName = from.replace(/<.*>/, "").trim();
  if (fromName && !fromName.includes("@")) return fromName;

  const hiMatch = text.match(/(?:hi|hello|dear)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/i);
  if (hiMatch) return hiMatch[1];

  const nameLine = text.match(/(?:name|from)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/i);
  if (nameLine) return nameLine[1];

  const signed = text.match(/(?:regards|thanks|cheers),?\s*\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/i);
  if (signed) return signed[1];

  return undefined;
}

function detectJobType(text: string): string {
  const lower = text.toLowerCase();
  for (const [type, keywords] of Object.entries(JOB_KEYWORDS)) {
    if (keywords.some((k) => lower.includes(k))) {
      return type.charAt(0).toUpperCase() + type.slice(1);
    }
  }
  return "general enquiry";
}

function detectUrgency(text: string): "routine" | "soon" | "emergency" {
  if (URGENCY_PATTERNS.emergency.test(text)) return "emergency";
  if (URGENCY_PATTERNS.soon.test(text)) return "soon";
  return "routine";
}

function extractPreferredDate(text: string): string | undefined {
  const m = text.match(
    /(?:on|for|by)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}\/\d{1,2}(?:\/\d{2,4})?)/i,
  );
  return m?.[1];
}

function cleanDescription(body: string): string {
  return body
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith(">"))
    .slice(0, 8)
    .join(" ")
    .slice(0, 500);
}
