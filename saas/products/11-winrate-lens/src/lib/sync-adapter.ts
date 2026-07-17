import type { Quote, SyncResult } from "./types";
import { computeResponseHours } from "./metrics";

const DEMO_QUOTES: Omit<Quote, "responseHours">[] = [
  {
    id: "q-001",
    externalId: "SM8-1042",
    source: "servicem8",
    jobType: "Hot water repair",
    suburb: "Parramatta",
    amountAud: 680,
    status: "won",
    quotedAt: "2026-06-01T09:00:00Z",
    respondedAt: "2026-06-01T10:30:00Z",
    closedAt: "2026-06-03T14:00:00Z",
  },
  {
    id: "q-002",
    externalId: "SM8-1043",
    source: "servicem8",
    jobType: "Blocked drain",
    suburb: "Blacktown",
    amountAud: 420,
    status: "won",
    quotedAt: "2026-06-02T11:00:00Z",
    respondedAt: "2026-06-02T12:00:00Z",
    closedAt: "2026-06-04T09:00:00Z",
  },
  {
    id: "q-003",
    externalId: "SM8-1044",
    source: "servicem8",
    jobType: "Bathroom renovation",
    suburb: "Castle Hill",
    amountAud: 8500,
    status: "lost",
    quotedAt: "2026-06-03T08:00:00Z",
    respondedAt: "2026-06-04T16:00:00Z",
    closedAt: "2026-06-10T10:00:00Z",
  },
  {
    id: "q-004",
    externalId: "SM8-1045",
    source: "servicem8",
    jobType: "Leak detection",
    suburb: "Parramatta",
    amountAud: 350,
    status: "won",
    quotedAt: "2026-06-05T14:00:00Z",
    respondedAt: "2026-06-05T15:00:00Z",
    closedAt: "2026-06-06T11:00:00Z",
  },
  {
    id: "q-005",
    externalId: "SM8-1046",
    source: "servicem8",
    jobType: "Hot water repair",
    suburb: "Penrith",
    amountAud: 720,
    status: "lost",
    quotedAt: "2026-06-06T10:00:00Z",
    respondedAt: "2026-06-07T18:00:00Z",
    closedAt: "2026-06-12T09:00:00Z",
  },
  {
    id: "q-006",
    externalId: "SM8-1047",
    source: "servicem8",
    jobType: "Blocked drain",
    suburb: "Parramatta",
    amountAud: 480,
    status: "won",
    quotedAt: "2026-06-08T09:30:00Z",
    respondedAt: "2026-06-08T10:00:00Z",
    closedAt: "2026-06-09T15:00:00Z",
  },
  {
    id: "q-007",
    externalId: "SM8-1048",
    source: "servicem8",
    jobType: "Tap replacement",
    suburb: "Blacktown",
    amountAud: 280,
    status: "lost",
    quotedAt: "2026-06-10T13:00:00Z",
    respondedAt: "2026-06-12T09:00:00Z",
    closedAt: "2026-06-15T10:00:00Z",
  },
  {
    id: "q-008",
    externalId: "SM8-1049",
    source: "servicem8",
    jobType: "Hot water repair",
    suburb: "Blacktown",
    amountAud: 650,
    status: "won",
    quotedAt: "2026-06-12T08:00:00Z",
    respondedAt: "2026-06-12T09:00:00Z",
    closedAt: "2026-06-13T14:00:00Z",
  },
  {
    id: "q-009",
    externalId: "SM8-1050",
    source: "servicem8",
    jobType: "Bathroom renovation",
    suburb: "Parramatta",
    amountAud: 12000,
    status: "lost",
    quotedAt: "2026-06-14T10:00:00Z",
    respondedAt: "2026-06-16T11:00:00Z",
    closedAt: "2026-06-20T09:00:00Z",
  },
  {
    id: "q-010",
    externalId: "SM8-1051",
    source: "servicem8",
    jobType: "Blocked drain",
    suburb: "Penrith",
    amountAud: 390,
    status: "open",
    quotedAt: "2026-06-16T11:00:00Z",
    respondedAt: "2026-06-16T12:30:00Z",
  },
];

function enrichQuote(q: Omit<Quote, "responseHours">): Quote {
  return {
    ...q,
    responseHours: computeResponseHours(q.quotedAt, q.respondedAt),
  };
}

export function mockServiceM8Sync(): SyncResult {
  if (process.env.SERVICEM8_API_KEY) {
    return { source: "servicem8", imported: 0, updated: 0, mockMode: false };
  }
  console.log("[MOCK ServiceM8] Synced demo quotes");
  return { source: "servicem8", imported: DEMO_QUOTES.length, updated: 0, mockMode: true };
}

export function getDemoQuotes(): Quote[] {
  return DEMO_QUOTES.map(enrichQuote);
}
