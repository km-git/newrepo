import { describe, it, expect } from "vitest";
import { buildSwms } from "./swms-builder";
import { selectHazards } from "./hazard-library";

describe("swms-builder", () => {
  const baseInput = {
    businessName: "Ace Electrical",
    siteAddress: "12 Smith St, Parramatta NSW",
    trade: "electrical" as const,
    jobDescription: "Replace switchboard and run new circuits",
    tasks: ["Isolate mains", "Install new board", "Test circuits"],
    siteConditions: ["Residential occupied", "Driveway access"],
    supervisor: "John Smith",
    workers: "2 electricians",
    emergencyContact: "000 / site manager 0400 000 000",
  };

  it("builds SWMS with hazards and disclaimer", () => {
    const doc = buildSwms(baseInput);
    expect(doc.hazards.length).toBeGreaterThan(0);
    expect(doc.bodyText).toContain("Ace Electrical");
    expect(doc.bodyText).toContain("DRAFT");
    expect(doc.disclaimer).toContain("does not provide safety");
    expect(doc.bodyText).toContain("Contact with live electrical");
  });

  it("selects hazards from job keywords", () => {
    const hazards = selectHazards(
      "plumbing",
      "Blocked drain in roof void with torch solder repair",
      ["Access roof void", "Solder joint"],
    );
    const ids = hazards.map((h) => h.id);
    expect(ids).toContain("plumb-confined");
    expect(ids).toContain("plumb-hot");
  });

  it("falls back to trade defaults when no keyword match", () => {
    const hazards = selectHazards("carpentry", "misc work", ["task"]);
    expect(hazards.length).toBeGreaterThan(0);
  });
});
