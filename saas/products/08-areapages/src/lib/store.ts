import type { AreaPage, PageInput } from "./types";
import { getSuburb } from "./suburb-data";
import { generatePage, scorePage } from "./page-generator";
import { publishToWordPress } from "./wordpress-adapter";

const globalStore = globalThis as typeof globalThis & {
  __apStore?: {
    pages: Map<string, AreaPage>;
  };
};

function store() {
  if (!globalStore.__apStore) {
    globalStore.__apStore = { pages: new Map() };
  }
  return globalStore.__apStore;
}

export function listPages(): AreaPage[] {
  return [...store().pages.values()].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function getPage(id: string): AreaPage | undefined {
  return store().pages.get(id);
}

export function createPage(input: PageInput): AreaPage | null {
  const suburb = getSuburb(input.suburbSlug);
  if (!suburb) return null;

  const draft = generatePage(input, suburb);
  const existingBodies = listPages()
    .filter((p) => p.input.suburbSlug !== input.suburbSlug)
    .map((p) => p.bodyText);

  const quality = scorePage(
    { bodyText: draft.bodyText, suburb, input },
    existingBodies,
  );

  const page: AreaPage = {
    ...draft,
    quality,
    status: quality.overall >= 70 ? "review" : "draft",
    createdAt: new Date().toISOString(),
  };

  store().pages.set(page.id, page);
  return page;
}

export function approvePage(id: string): AreaPage | null {
  const page = store().pages.get(id);
  if (!page) return null;
  page.status = "approved";
  return page;
}

export function publishPage(id: string): { page: AreaPage; result: ReturnType<typeof publishToWordPress> } | null {
  const page = store().pages.get(id);
  if (!page || page.status !== "approved") return null;

  const result = publishToWordPress(page);
  if (result.success) {
    page.status = "published";
    page.wordpressPostId = result.postId;
    page.publishedAt = new Date().toISOString();
  }
  return { page, result };
}

export function seedDemoPages(): AreaPage[] {
  const inputs: PageInput[] = [
    {
      businessName: "Ace Plumbing Sydney",
      service: "Emergency Plumber",
      trade: "Plumber",
      suburbSlug: "parramatta",
      jobReferences: ["blocked drain on Macquarie St", "hot water unit in Harris Park"],
      phone: "1300 000 111",
    },
    {
      businessName: "Ace Plumbing Sydney",
      service: "Emergency Plumber",
      trade: "Plumber",
      suburbSlug: "penrith",
      jobReferences: ["burst pipe near Nepean River"],
      phone: "1300 000 111",
    },
  ];

  return inputs.map((input) => createPage(input)!).filter(Boolean);
}

export function isMockMode(): boolean {
  return !process.env.WORDPRESS_URL;
}

export function resetStore(): void {
  globalStore.__apStore = undefined;
}
