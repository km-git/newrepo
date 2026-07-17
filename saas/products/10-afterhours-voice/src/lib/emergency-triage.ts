import type { EmergencyCriteria, Urgency } from "./types";

export function isEmergency(
  urgency: Urgency | undefined,
  details: string,
  criteria: EmergencyCriteria,
): boolean {
  if (urgency && criteria.escalateUrgencies.includes(urgency)) {
    return true;
  }
  const lower = details.toLowerCase();
  return criteria.keywords.some((kw) => lower.includes(kw.toLowerCase()));
}

export function escalationMessage(
  businessName: string,
  suburb: string,
  jobType: string,
  details: string,
): string {
  return `[${businessName} ON-CALL] Emergency after-hours call from ${suburb}: ${jobType}. ${details}`;
}
