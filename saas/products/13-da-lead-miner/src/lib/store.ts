import type { DevelopmentApplication, UserProfile, WeeklyDigest } from "./types";
import { DEMO_COUNCILS, fetchAllDemoLeads, fetchCouncilFeed } from "./feed-adapters";
import { generateWeeklyDigest } from "./digest-generator";

const globalStore = globalThis as typeof globalThis & {
  __dalmStore?: {
    profile: UserProfile;
    leads: Map<string, DevelopmentApplication>;
    lastDigest?: WeeklyDigest;
    lastSyncAt?: string;
  };
};

function store() {
  if (!globalStore.__dalmStore) {
    const profile: UserProfile = {
      businessName: "Summit Pool & Landscape",
      tradeFocus: "pool_builder",
      councils: ["parramatta", "blacktown", "hills"],
    };
    const leads = new Map<string, DevelopmentApplication>();
    for (const lead of fetchAllDemoLeads(profile.tradeFocus)) {
      leads.set(lead.id, lead);
    }
    globalStore.__dalmStore = {
      profile,
      leads,
      lastDigest: generateWeeklyDigest([...leads.values()]),
      lastSyncAt: new Date().toISOString(),
    };
  }
  return globalStore.__dalmStore;
}

export function getProfile(): UserProfile {
  return store().profile;
}

export function listCouncils() {
  return DEMO_COUNCILS.filter((c) => store().profile.councils.includes(c.id));
}

export function listLeads(): DevelopmentApplication[] {
  return [...store().leads.values()].sort((a, b) => b.leadScore - a.leadScore);
}

export function getLead(id: string): DevelopmentApplication | undefined {
  return store().leads.get(id);
}

export function updateLeadStatus(
  id: string,
  status: DevelopmentApplication["status"],
): DevelopmentApplication | null {
  const lead = store().leads.get(id);
  if (!lead) return null;
  lead.status = status;
  return lead;
}

export function syncCouncil(councilId: string) {
  const imported = fetchCouncilFeed(councilId, store().profile.tradeFocus);
  for (const lead of imported) {
    const existing = store().leads.get(lead.id);
    if (!existing) {
      store().leads.set(lead.id, lead);
    }
  }
  store().lastSyncAt = new Date().toISOString();
  store().lastDigest = generateWeeklyDigest(listLeads());
  return {
    councilId,
    imported: imported.length,
    mockMode: !process.env.DA_FEED_API_KEY,
    lastSyncAt: store().lastSyncAt,
  };
}

export function syncAllCouncils() {
  const results = store().profile.councils.map((id) => syncCouncil(id));
  return results;
}

export function getDigest(): WeeklyDigest {
  const digest = generateWeeklyDigest(listLeads());
  store().lastDigest = digest;
  return digest;
}

export function getLastSyncAt(): string | undefined {
  return store().lastSyncAt;
}

export function isMockMode(): boolean {
  return !process.env.DA_FEED_API_KEY;
}

export function resetStore(): void {
  globalStore.__dalmStore = undefined;
}
