import type { TradeTemplate } from "./types";

export interface TemplateSection {
  id: string;
  title: string;
  prompt: string;
}

export const REPORT_TEMPLATES: Record<TradeTemplate, { name: string; sections: TemplateSection[] }> = {
  electrical: {
    name: "Electrical Completion Report",
    sections: [
      { id: "scope", title: "Scope of Work", prompt: "What electrical work was completed?" },
      { id: "testing", title: "Testing & Compliance", prompt: "Test results, RCD/safety switch checks" },
      { id: "materials", title: "Materials Installed", prompt: "Key components replaced or installed" },
      { id: "recommendations", title: "Recommendations", prompt: "Follow-up work or maintenance advice" },
    ],
  },
  pest: {
    name: "Pest Inspection Report",
    sections: [
      { id: "inspection", title: "Inspection Summary", prompt: "Areas inspected and methods used" },
      { id: "findings", title: "Findings", prompt: "Evidence of pest activity or damage" },
      { id: "treatment", title: "Treatment Applied", prompt: "Products and areas treated" },
      { id: "recommendations", title: "Recommendations", prompt: "Prevention and follow-up" },
    ],
  },
  solar: {
    name: "Solar Installation Report",
    sections: [
      { id: "system", title: "System Details", prompt: "Panels, inverter, capacity installed" },
      { id: "commissioning", title: "Commissioning", prompt: "Startup checks and monitoring setup" },
      { id: "safety", title: "Safety & Compliance", prompt: "Isolators, labelling, roof penetrations" },
      { id: "recommendations", title: "Recommendations", prompt: "Maintenance and monitoring advice" },
    ],
  },
  maintenance: {
    name: "Property Maintenance Report",
    sections: [
      { id: "work", title: "Work Completed", prompt: "Tasks completed on site" },
      { id: "condition", title: "Condition Notes", prompt: "Observed condition of assets" },
      { id: "issues", title: "Issues Found", prompt: "Defects or concerns identified" },
      { id: "recommendations", title: "Recommendations", prompt: "Suggested follow-up actions" },
    ],
  },
};

export function getTemplate(trade: TradeTemplate) {
  return REPORT_TEMPLATES[trade];
}
