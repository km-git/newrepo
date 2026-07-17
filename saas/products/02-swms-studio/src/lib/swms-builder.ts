import { randomUUID } from "crypto";
import type { SwmsDocument, SwmsInput } from "./types";
import { selectHazards } from "./hazard-library";

const DISCLAIMER =
  "DRAFT — This Safe Work Method Statement is generated as a documentation aid only. " +
  "The PCBU and workers must review, amend, and sign off before work commences. " +
  "This tool does not provide safety or legal advice.";

export function buildSwms(input: SwmsInput): SwmsDocument {
  const hazards = selectHazards(input.trade, input.jobDescription, input.tasks);
  const generatedAt = new Date().toISOString();

  const sections = [
    `SAFE WORK METHOD STATEMENT (DRAFT)`,
    ``,
    `Business: ${input.businessName}`,
    `Site: ${input.siteAddress}`,
    `Trade: ${input.trade}`,
    `Supervisor: ${input.supervisor}`,
    `Workers: ${input.workers}`,
    `Emergency contact: ${input.emergencyContact}`,
    `Generated: ${generatedAt}`,
    ``,
    `JOB DESCRIPTION`,
    input.jobDescription,
    ``,
    `TASKS`,
    ...input.tasks.map((t, i) => `${i + 1}. ${t}`),
    ``,
    `SITE CONDITIONS`,
    ...input.siteConditions.map((c) => `- ${c}`),
    ``,
    `HAZARDS, RISKS & CONTROLS`,
    ...hazards.flatMap((h, i) => [
      ``,
      `${i + 1}. ${h.hazard}`,
      `   Risk: ${h.risk}`,
      `   Controls:`,
      ...h.controls.map((c) => `     • ${c}`),
      `   PPE: ${h.ppe.join(", ")}`,
    ]),
    ``,
    `SIGN-OFF (complete on site)`,
    `Supervisor signature: _________________ Date: _______`,
    `Worker signatures: ____________________ Date: _______`,
    ``,
    DISCLAIMER,
  ];

  return {
    id: randomUUID(),
    input,
    hazards,
    disclaimer: DISCLAIMER,
    generatedAt,
    bodyText: sections.join("\n"),
  };
}
