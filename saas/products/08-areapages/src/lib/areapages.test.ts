import { describe, it, expect, beforeEach } from "vitest";
import { generatePage, scorePage } from "./page-generator";
import { getSuburb, listSuburbs } from "./suburb-data";
import { resetStore, createPage, approvePage, publishPage, seedDemoPages } from "./store";
import type { PageInput } from "./types";

const baseInput: PageInput = {
  businessName: "Test Trades Co",
  service: "Electrician",
  trade: "Electrical",
  suburbSlug: "parramatta",
  jobReferences: ["switchboard upgrade on George St"],
  phone: "0400 000 000",
};

describe("suburb-data", () => {
  it("lists NSW suburbs with landmarks", () => {
    expect(listSuburbs().length).toBeGreaterThanOrEqual(4);
    const p = getSuburb("parramatta");
    expect(p?.landmarks).toContain("Parramatta Square");
  });
});

describe("page-generator", () => {
  it("generates locally grounded page", () => {
    const suburb = getSuburb("penrith")!;
    const page = generatePage(baseInput, suburb);
    expect(page.title).toContain("Penrith");
    expect(page.bodyText).toContain("Penrith City Council");
    expect(page.bodyText).toContain("Nepean River");
    expect(page.metaDescription).toContain("2750");
  });

  it("scores uniqueness against existing pages", () => {
    const suburb = getSuburb("parramatta")!;
    const page = generatePage(baseInput, suburb);
    const score = scorePage({ bodyText: page.bodyText, suburb, input: baseInput }, [page.bodyText]);
    expect(score.warnings.some((w) => w.includes("similarity"))).toBe(true);
    expect(score.localGrounding).toBeGreaterThan(50);
  });
});

describe("store workflow", () => {
  beforeEach(() => resetStore());

  it("creates page in review status when quality is good", () => {
    const page = createPage({ ...baseInput, suburbSlug: "blacktown" });
    expect(page).toBeDefined();
    expect(page!.quality.overall).toBeGreaterThan(0);
    expect(["draft", "review"]).toContain(page!.status);
  });

  it("publishes after approval", () => {
    seedDemoPages();
    const page = createPage({ ...baseInput, suburbSlug: "liverpool" })!;
    approvePage(page.id);
    const result = publishPage(page.id);
    expect(result?.result.success).toBe(true);
    expect(result?.page.status).toBe("published");
  });
});
