import { randomUUID } from "crypto";
import type { VoiceNote } from "./types";
import { getTemplate } from "./report-templates";
import type { TradeTemplate } from "./types";

const SECTION_KEYWORDS: Record<string, RegExp> = {
  scope: /installed|replaced|completed|wired|upgraded/i,
  testing: /test|rcd|safety switch|compliance|passed/i,
  materials: /cable|switchboard|panel|inverter|component/i,
  inspection: /inspected|checked|examined|surveyed/i,
  findings: /found|evidence|activity|damage|termites|rodent/i,
  treatment: /treated|sprayed|bait|applied/i,
  system: /panel|inverter|kw|kilowatt|array/i,
  commissioning: /commission|startup|monitoring|connected/i,
  safety: /isolator|label|penetration|safety/i,
  work: /fixed|repaired|maintained|serviced/i,
  condition: /condition|wear|corrosion|rust/i,
  issues: /issue|defect|concern|leak|crack/i,
  recommendations: /recommend|suggest|follow.?up|should|advise/i,
};

export function parseVoiceNotes(
  transcripts: string[],
  trade: TradeTemplate,
): VoiceNote[] {
  const template = getTemplate(trade);
  const notes: VoiceNote[] = [];

  for (const t of transcripts) {
    const section = matchSection(t, template.sections.map((s) => s.id));
    notes.push({
      id: randomUUID(),
      transcript: t.trim(),
      section,
    });
  }

  return notes;
}

function matchSection(text: string, sectionIds: string[]): string | undefined {
  for (const id of sectionIds) {
    const re = SECTION_KEYWORDS[id];
    if (re?.test(text)) return id;
  }
  if (/recommend|suggest|follow/i.test(text)) return "recommendations";
  return sectionIds[0];
}

export function structureTranscript(raw: string): string {
  return raw
    .trim()
    .replace(/\s+/g, " ")
    .replace(/^um,?\s*/i, "")
    .replace(/\.\s+/g, ". ")
    .slice(0, 500);
}
