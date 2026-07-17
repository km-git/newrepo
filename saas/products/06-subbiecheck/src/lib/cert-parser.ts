import type { DocumentType, ParsedFields } from "./types";

const EXPIRY_RE =
  /(?:expir(?:y|es|ed)|valid until|valid to)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}-\d{2}-\d{2})/i;
const AMOUNT_RE = /\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|m))?/i;
const POLICY_RE = /(?:policy|certificate|ref)[#:\s]*([A-Z0-9\-]+)/i;
const LICENCE_RE = /(?:licen[cs]e|lic)[#:\s]*([A-Z0-9\-]+)/i;
const INSURER_RE =
  /(?:insurer|underwriter|issued by)[:\s]*([A-Za-z\s&]+?)(?:\.|,|\n|$)/i;

export function detectDocumentType(fileName: string, text: string): DocumentType {
  const combined = `${fileName} ${text}`.toLowerCase();
  if (/public liability|pli|liability insurance/.test(combined)) return "public_liability";
  if (/workers comp|workcover|workers compensation/.test(combined)) return "workers_comp";
  if (/white[\s_-]?card|construction induction/.test(combined)) return "white_card";
  if (/swms|safe work method/.test(combined)) return "swms_acknowledgement";
  if (/licen[cs]e|contractor licence|trade licence/.test(combined)) return "trade_licence";
  return "public_liability";
}

export function parseCertificate(
  fileName: string,
  rawText: string,
): ParsedFields {
  const expiryMatch = rawText.match(EXPIRY_RE);
  let expiryDate = expiryMatch?.[1] ?? "";

  if (!expiryDate) {
    const iso = rawText.match(/\b(20\d{2}-\d{2}-\d{2})\b/);
    expiryDate = iso?.[1] ?? "";
  }

  if (!expiryDate && /expir/i.test(fileName)) {
    const fileDate = fileName.match(/(20\d{2})[\/\-](\d{2})[\/\-](\d{2})/);
    if (fileDate) expiryDate = `${fileDate[1]}-${fileDate[2]}-${fileDate[3]}`;
  }

  const amount = rawText.match(AMOUNT_RE)?.[0];
  const policy = rawText.match(POLICY_RE)?.[1];
  const licence = rawText.match(LICENCE_RE)?.[1];
  const insurer = rawText.match(INSURER_RE)?.[1]?.trim();

  const fieldsPresent = [expiryDate, amount, policy, licence, insurer].filter(Boolean).length;
  const confidence =
    fieldsPresent >= 3 && expiryDate ? "high" : fieldsPresent >= 1 ? "medium" : "low";

  return {
    expiryDate: normaliseDate(expiryDate),
    coverageAmount: amount,
    policyNumber: policy,
    licenceNumber: licence,
    insurer,
    confidence,
  };
}

function normaliseDate(d: string): string {
  if (!d) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(d)) return d;
  const parts = d.split(/[\/\-]/);
  if (parts.length === 3) {
    if (parts[0].length === 4) return `${parts[0]}-${parts[1].padStart(2, "0")}-${parts[2].padStart(2, "0")}`;
    const [day, month, year] = parts;
    const y = year.length === 2 ? `20${year}` : year;
    return `${y}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }
  return d;
}

export function daysUntilExpiry(expiryDate: string, now = new Date()): number | null {
  if (!expiryDate) return null;
  const exp = new Date(expiryDate);
  if (Number.isNaN(exp.getTime())) return null;
  return Math.ceil((exp.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

export function expiryStatus(
  expiryDate: string,
  warningDays = 30,
): "valid" | "expiring" | "expired" | "unknown" {
  const days = daysUntilExpiry(expiryDate);
  if (days === null) return "unknown";
  if (days < 0) return "expired";
  if (days <= warningDays) return "expiring";
  return "valid";
}
