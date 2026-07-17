export type Trade = "electrical" | "plumbing" | "carpentry" | "general";

export interface HazardControl {
  id: string;
  hazard: string;
  risk: string;
  controls: string[];
  ppe: string[];
}

export interface SwmsInput {
  businessName: string;
  siteAddress: string;
  trade: Trade;
  jobDescription: string;
  tasks: string[];
  siteConditions: string[];
  supervisor: string;
  workers: string;
  emergencyContact: string;
}

export interface SwmsDocument {
  id: string;
  input: SwmsInput;
  hazards: HazardControl[];
  disclaimer: string;
  generatedAt: string;
  bodyText: string;
}
