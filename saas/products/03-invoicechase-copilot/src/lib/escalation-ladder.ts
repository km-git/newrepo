import type { ReminderTone, ChaseStage } from "./types";

export interface EscalationStep {
  stage: ChaseStage;
  tone: ReminderTone;
  daysAfterDue: number;
  channel: "email" | "sms";
  label: string;
}

/** Default ladder: friendly → firm → final. Reminders only — not debt collection. */
export const ESCALATION_LADDER: EscalationStep[] = [
  { stage: 1, tone: "friendly", daysAfterDue: 7, channel: "email", label: "Friendly nudge" },
  { stage: 2, tone: "firm", daysAfterDue: 21, channel: "email", label: "Firm reminder" },
  { stage: 3, tone: "final", daysAfterDue: 35, channel: "email", label: "Final notice" },
];

export function toneForStage(stage: ChaseStage): ReminderTone {
  if (stage <= 0) return "friendly";
  const step = ESCALATION_LADDER.find((s) => s.stage === stage);
  return step?.tone ?? "final";
}

export function nextStage(current: ChaseStage): ChaseStage | null {
  if (current >= 3) return null;
  return (current + 1) as ChaseStage;
}

export function stageForDaysOverdue(daysOverdue: number): ChaseStage {
  let stage: ChaseStage = 0;
  for (const step of ESCALATION_LADDER) {
    if (daysOverdue >= step.daysAfterDue) stage = step.stage;
  }
  return stage;
}

export function daysUntilNextStep(
  daysOverdue: number,
  currentStage: ChaseStage,
): number | null {
  const next = ESCALATION_LADDER.find((s) => s.stage === currentStage + 1);
  if (!next) return null;
  return Math.max(0, next.daysAfterDue - daysOverdue);
}
