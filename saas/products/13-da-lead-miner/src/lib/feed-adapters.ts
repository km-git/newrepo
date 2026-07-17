import type { Council, DevelopmentApplication } from "./types";
import { classifyWorkTypes, tradesForWorkTypes, draftLeadReason } from "./da-classifier";
import { scoreLead } from "./lead-scorer";

export const DEMO_COUNCILS: Council[] = [
  { id: "parramatta", name: "City of Parramatta", region: "Western Sydney" },
  { id: "blacktown", name: "Blacktown City Council", region: "Western Sydney" },
  { id: "hills", name: "The Hills Shire Council", region: "North West Sydney" },
];

interface RawDa {
  daNumber: string;
  address: string;
  suburb: string;
  description: string;
  approvedAt: string;
  councilId: string;
}

const RAW_FEED: RawDa[] = [
  {
    councilId: "parramatta",
    daNumber: "DA-2026-0142",
    address: "12 River Rd",
    suburb: "Ermington",
    description: "Swimming pool and spa with retaining walls and landscaping",
    approvedAt: new Date(Date.now() - 3 * 86400000).toISOString(),
  },
  {
    councilId: "parramatta",
    daNumber: "DA-2026-0138",
    address: "45 Victoria Ave",
    suburb: "Parramatta",
    description: "Two-storey extension and kitchen renovation",
    approvedAt: new Date(Date.now() - 10 * 86400000).toISOString(),
  },
  {
    councilId: "blacktown",
    daNumber: "DA-2026-0091",
    address: "8 Oak St",
    suburb: "Blacktown",
    description: "Solar panel and battery installation with switchboard upgrade",
    approvedAt: new Date(Date.now() - 5 * 86400000).toISOString(),
  },
  {
    councilId: "blacktown",
    daNumber: "DA-2026-0087",
    address: "22 Park Ln",
    suburb: "Seven Hills",
    description: "Bathroom renovation and plumbing alterations",
    approvedAt: new Date(Date.now() - 18 * 86400000).toISOString(),
  },
  {
    councilId: "hills",
    daNumber: "DA-2026-0203",
    address: "3 Hillview Cres",
    suburb: "Castle Hill",
    description: "Granny flat extension with deck and pergola",
    approvedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
  {
    councilId: "hills",
    daNumber: "DA-2026-0198",
    address: "77 Showground Rd",
    suburb: "Baulkham Hills",
    description: "Demolition of existing garage and new landscaping works",
    approvedAt: new Date(Date.now() - 12 * 86400000).toISOString(),
  },
  {
    councilId: "parramatta",
    daNumber: "DA-2026-0155",
    address: "9 Meadow Cl",
    suburb: "North Parramatta",
    description: "EV charger and electrical sub-board installation",
    approvedAt: new Date(Date.now() - 6 * 86400000).toISOString(),
  },
  {
    councilId: "blacktown",
    daNumber: "DA-2026-0099",
    address: "14 Wattle Dr",
    suburb: "Mount Druitt",
    description: "In-ground swimming pool with glass fencing",
    approvedAt: new Date(Date.now() - 4 * 86400000).toISOString(),
  },
];

function daysSince(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
}

export function parseRawDa(
  raw: RawDa,
  tradeFocus: import("./types").TradeFocus,
): DevelopmentApplication {
  const workTypes = classifyWorkTypes(raw.description);
  const tradesNeeded = tradesForWorkTypes(workTypes);
  const leadScore = scoreLead(workTypes, tradesNeeded, tradeFocus, daysSince(raw.approvedAt));
  return {
    id: `${raw.councilId}-${raw.daNumber}`,
    councilId: raw.councilId,
    daNumber: raw.daNumber,
    address: raw.address,
    suburb: raw.suburb,
    description: raw.description,
    approvedAt: raw.approvedAt,
    workTypes,
    tradesNeeded,
    leadScore,
    leadReason: draftLeadReason(raw.description, workTypes, tradeFocus),
    status: "new",
  };
}

export function fetchCouncilFeed(
  councilId: string,
  tradeFocus: import("./types").TradeFocus,
): DevelopmentApplication[] {
  if (process.env.DA_FEED_API_KEY) {
    return [];
  }
  console.log(`[MOCK DA FEED] Fetching ${councilId}`);
  return RAW_FEED.filter((r) => r.councilId === councilId).map((r) => parseRawDa(r, tradeFocus));
}

export function fetchAllDemoLeads(tradeFocus: import("./types").TradeFocus): DevelopmentApplication[] {
  return RAW_FEED.map((r) => parseRawDa(r, tradeFocus));
}
