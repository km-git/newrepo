import type { EvidenceItem, PracticeStandard } from "./types";

const KEYWORD_MAP: Record<string, string[]> = {
  "1.1": ["service agreement", "consent", "choice", "participant information"],
  "1.2": ["privacy", "confidential", "dignity"],
  "2.1": ["governance", "board", "minutes", "organisational chart", "strategic"],
  "2.2": ["risk register", "incident management", "risk assessment"],
  "2.3": ["quality", "audit", "continuous improvement", "feedback"],
  "3.1": ["support plan", "planning", "review"],
  "3.2": ["competency", "training", "supervision", "certificate"],
  "4.1": ["whs", "safety", "workplace health", "maintenance"],
  "4.2": ["incident", "reportable", "procedure"],
};

export function matchEvidenceToStandards(
  evidence: Pick<EvidenceItem, "title" | "documentRef">,
  standards: PracticeStandard[] = [],
): string[] {
  const text = `${evidence.title} ${evidence.documentRef}`.toLowerCase();
  const matched: string[] = [];

  for (const std of standards.length ? standards : Object.keys(KEYWORD_MAP)) {
    const id = typeof std === "string" ? std : std.id;
    const keywords = KEYWORD_MAP[id] ?? [];
    if (keywords.some((k) => text.includes(k))) {
      matched.push(id);
    }
  }

  return matched;
}
