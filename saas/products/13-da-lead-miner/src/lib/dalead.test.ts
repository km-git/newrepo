import { describe, it, expect, beforeEach } from "vitest";
import { classifyWorkTypes, tradesForWorkTypes, draftLeadReason, matchesTradeFocus } from "./da-classifier";
import { scoreLead, scoreLabel } from "./lead-scorer";
import { fetchAllDemoLeads, parseRawDa } from "./feed-adapters";
import { generateWeeklyDigest } from "./digest-generator";
import {
  resetStore,
  listLeads,
  listCouncils,
  getDigest,
  syncCouncil,
  updateLeadStatus,
  getProfile,
  isMockMode,
} from "./store";

describe("da-classifier", () => {
  it("classifies pool work", () => {
    const types = classifyWorkTypes("Swimming pool and spa with landscaping");
    expect(types).toContain("pool");
    expect(types).toContain("landscaping");
  });

  it("classifies electrical work", () => {
    expect(classifyWorkTypes("Solar panel and switchboard upgrade")).toContain("electrical");
  });

  it("maps trades from work types", () => {
    const trades = tradesForWorkTypes(["pool", "electrical"]);
    expect(trades).toContain("pool builder");
    expect(trades).toContain("electrician");
  });

  it("drafts lead reason", () => {
    const reason = draftLeadReason("Pool and spa", ["pool"], "pool_builder");
    expect(reason).toContain("pool");
    expect(reason.length).toBeGreaterThan(20);
  });

  it("matches trade focus", () => {
    expect(matchesTradeFocus(["pool builder", "electrician"], "pool_builder")).toBe(true);
    expect(matchesTradeFocus(["electrician"], "pool_builder")).toBe(false);
  });
});

describe("lead-scorer", () => {
  it("scores recent pool leads highly for pool builders", () => {
    const score = scoreLead(["pool", "landscaping"], ["pool builder"], "pool_builder", 3);
    expect(score).toBeGreaterThanOrEqual(75);
    expect(scoreLabel(score)).toBe("hot");
  });

  it("labels score tiers", () => {
    expect(scoreLabel(80)).toBe("hot");
    expect(scoreLabel(60)).toBe("warm");
    expect(scoreLabel(40)).toBe("cool");
  });
});

describe("feed-adapters", () => {
  it("parses raw DA into lead", () => {
    const lead = parseRawDa(
      {
        councilId: "parramatta",
        daNumber: "DA-TEST",
        address: "1 Test St",
        suburb: "Parramatta",
        description: "Kitchen renovation",
        approvedAt: new Date().toISOString(),
      },
      "builder",
    );
    expect(lead.leadScore).toBeGreaterThan(0);
    expect(lead.workTypes).toContain("renovation");
  });

  it("loads demo feed", () => {
    expect(fetchAllDemoLeads("pool_builder").length).toBe(8);
  });
});

describe("digest-generator", () => {
  it("generates weekly digest", () => {
    const leads = fetchAllDemoLeads("pool_builder");
    const digest = generateWeeklyDigest(leads);
    expect(digest.leadCount).toBe(8);
    expect(digest.topLeads.length).toBeLessThanOrEqual(5);
    expect(digest.summary.length).toBeGreaterThan(10);
  });
});

describe("store", () => {
  beforeEach(() => resetStore());

  it("loads demo leads", () => {
    expect(listLeads().length).toBe(8);
  });

  it("lists monitored councils", () => {
    expect(listCouncils().length).toBe(3);
  });

  it("updates lead status", () => {
    const lead = listLeads()[0];
    const updated = updateLeadStatus(lead.id, "saved");
    expect(updated?.status).toBe("saved");
  });

  it("syncs council feed in mock mode", () => {
    expect(isMockMode()).toBe(true);
    const result = syncCouncil("parramatta");
    expect(result.mockMode).toBe(true);
    expect(result.imported).toBeGreaterThan(0);
  });

  it("returns digest", () => {
    const digest = getDigest();
    expect(digest.topLeads.length).toBeGreaterThan(0);
  });

  it("uses pool builder profile", () => {
    expect(getProfile().tradeFocus).toBe("pool_builder");
  });
});
