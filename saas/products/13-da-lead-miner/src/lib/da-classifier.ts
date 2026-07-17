import type { TradeFocus, WorkType } from "./types";

const WORK_KEYWORDS: Record<WorkType, string[]> = {
  pool: ["pool", "swimming", "spa"],
  renovation: ["renovation", "alteration", "kitchen", "bathroom", "refurbish"],
  extension: ["extension", "addition", "second storey", "granny flat"],
  electrical: ["solar", "electrical", "switchboard", "ev charger", "battery"],
  landscaping: ["landscap", "retaining wall", "deck", "pergola", "outdoor"],
  demolition: ["demolition", "demolish"],
  other: [],
};

const TRADE_MAP: Record<WorkType, string[]> = {
  pool: ["pool builder", "electrician", "plumber", "landscaper"],
  renovation: ["builder", "plumber", "electrician", "tiler"],
  extension: ["builder", "electrician", "plumber"],
  electrical: ["electrician", "solar installer"],
  landscaping: ["landscaper", "builder"],
  demolition: ["builder", "demolition contractor"],
  other: ["builder"],
};

export function classifyWorkTypes(description: string): WorkType[] {
  const lower = description.toLowerCase();
  const found: WorkType[] = [];
  for (const [type, keywords] of Object.entries(WORK_KEYWORDS) as [WorkType, string[]][]) {
    if (type === "other") continue;
    if (keywords.some((kw) => lower.includes(kw))) {
      found.push(type);
    }
  }
  return found.length > 0 ? found : ["other"];
}

export function tradesForWorkTypes(workTypes: WorkType[]): string[] {
  const trades = new Set<string>();
  for (const wt of workTypes) {
    for (const t of TRADE_MAP[wt]) trades.add(t);
  }
  return [...trades];
}

export function draftLeadReason(
  description: string,
  workTypes: WorkType[],
  tradeFocus: TradeFocus,
): string {
  const focus = tradeFocus === "all" ? "trades" : tradeFocus.replace("_", " ");
  const primary = workTypes[0] === "other" ? "building" : workTypes[0];
  const snippet = description.length > 60 ? `${description.slice(0, 57)}…` : description;
  return `New ${primary} approval in your patch — likely needs a ${focus} for: ${snippet}`;
}

export function matchesTradeFocus(tradesNeeded: string[], focus: TradeFocus): boolean {
  if (focus === "all") return true;
  const normalized = focus.replace("_", " ");
  return tradesNeeded.some((t) => t.includes(normalized) || normalized.includes(t.split(" ")[0]));
}
