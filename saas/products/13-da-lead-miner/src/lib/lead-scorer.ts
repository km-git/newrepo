import type { TradeFocus, WorkType } from "./types";
import { matchesTradeFocus } from "./da-classifier";

const WORK_VALUE: Record<WorkType, number> = {
  pool: 25,
  extension: 22,
  renovation: 20,
  electrical: 15,
  landscaping: 12,
  demolition: 10,
  other: 5,
};

export function scoreLead(
  workTypes: WorkType[],
  tradesNeeded: string[],
  tradeFocus: TradeFocus,
  daysSinceApproval: number,
): number {
  let score = 40;

  if (matchesTradeFocus(tradesNeeded, tradeFocus)) score += 25;

  for (const wt of workTypes) {
    score += WORK_VALUE[wt] ?? 0;
  }

  if (daysSinceApproval <= 7) score += 15;
  else if (daysSinceApproval <= 14) score += 8;

  return Math.min(100, score);
}

export function scoreLabel(score: number): "hot" | "warm" | "cool" {
  if (score >= 75) return "hot";
  if (score >= 55) return "warm";
  return "cool";
}
