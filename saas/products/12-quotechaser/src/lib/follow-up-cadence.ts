import type { FollowUpStage, FollowUpTone } from "./types";

export const DEFAULT_CADENCE_DAYS = [3, 7, 14];

export function stageForDays(daysSinceSent: number, cadence = DEFAULT_CADENCE_DAYS): FollowUpStage {
  if (daysSinceSent >= cadence[2]) return 3;
  if (daysSinceSent >= cadence[1]) return 2;
  if (daysSinceSent >= cadence[0]) return 1;
  return 0;
}

export function toneForStage(stage: FollowUpStage): FollowUpTone {
  if (stage === 1) return "gentle";
  if (stage === 2) return "friendly";
  return "firm";
}

export function nextActionDate(sentAt: string, stage: FollowUpStage, cadence = DEFAULT_CADENCE_DAYS): string {
  const dayOffset = cadence[Math.min(stage, cadence.length - 1) - 1] ?? cadence[0];
  const d = new Date(sentAt);
  d.setDate(d.getDate() + dayOffset);
  return d.toISOString();
}

export function isDueForFollowUp(
  daysSinceSent: number,
  followUpsSent: number,
  cadence = DEFAULT_CADENCE_DAYS,
): boolean {
  const stage = stageForDays(daysSinceSent, cadence);
  return stage > followUpsSent && stage > 0;
}
