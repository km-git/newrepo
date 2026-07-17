import type { PracticeStandard } from "./types";

/** Subset of NDIS Practice Standards indicators (public framework — informational mapping only). */
export const PRACTICE_STANDARDS: PracticeStandard[] = [
  {
    id: "1.1",
    module: "Rights and responsibilities",
    outcome: "Person-centred supports",
    indicator: "Each participant exercises choice and control over their supports",
    evidenceHint: "Service agreements, participant information sheets, consent records",
  },
  {
    id: "1.2",
    module: "Rights and responsibilities",
    outcome: "Privacy and dignity",
    indicator: "Participants' privacy and dignity are respected",
    evidenceHint: "Privacy policy, confidentiality procedures, staff training records",
  },
  {
    id: "2.1",
    module: "Governance and operational management",
    outcome: "Governance",
    indicator: "The organisation is effectively governed",
    evidenceHint: "Board/owner meeting minutes, organisational chart, strategic plan",
  },
  {
    id: "2.2",
    module: "Governance and operational management",
    outcome: "Risk management",
    indicator: "Risks to participants and the organisation are identified and managed",
    evidenceHint: "Risk register, incident management policy, incident logs (de-identified)",
  },
  {
    id: "2.3",
    module: "Governance and operational management",
    outcome: "Quality management",
    indicator: "The organisation has a quality management system",
    evidenceHint: "Internal audit schedule, continuous improvement register, feedback process",
  },
  {
    id: "3.1",
    module: "Provision of supports",
    outcome: "Support planning",
    indicator: "Supports are planned with the participant",
    evidenceHint: "Support plan templates, review schedules (no participant PII stored)",
  },
  {
    id: "3.2",
    module: "Provision of supports",
    outcome: "Service delivery",
    indicator: "Supports are delivered safely and competently",
    evidenceHint: "Staff competency matrix, supervision records, training certificates",
  },
  {
    id: "4.1",
    module: "Support provision environment",
    outcome: "Safe environment",
    indicator: "The environment is safe and fit for purpose",
    evidenceHint: "Workplace health and safety checks, equipment maintenance logs",
  },
  {
    id: "4.2",
    module: "Support provision environment",
    outcome: "Incident management",
    indicator: "Incidents are managed and reported appropriately",
    evidenceHint: "Incident management policy, reportable incident procedure, staff training",
  },
];

export function getStandard(id: string): PracticeStandard | undefined {
  return PRACTICE_STANDARDS.find((s) => s.id === id);
}
