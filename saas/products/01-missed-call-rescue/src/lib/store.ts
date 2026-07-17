import { randomUUID } from "crypto";
import type { BusinessProfile, LeadCard, SmsSession } from "./types";

const globalStore = globalThis as typeof globalThis & {
  __mcrStore?: {
    leads: Map<string, LeadCard>;
    sessions: Map<string, SmsSession>;
    businesses: Map<string, BusinessProfile>;
  };
};

function store() {
  if (!globalStore.__mcrStore) {
    const demo: BusinessProfile = {
      id: "demo",
      name: "Demo Plumbing Co",
      trade: "plumber",
      twilioNumber: "+61400000000",
      ownerPhone: "+61400000001",
    };
    globalStore.__mcrStore = {
      leads: new Map(),
      sessions: new Map(),
      businesses: new Map([["demo", demo]]),
    };
  }
  return globalStore.__mcrStore;
}

export function getBusiness(id = "demo"): BusinessProfile | undefined {
  return store().businesses.get(id);
}

export function listLeads(): LeadCard[] {
  return [...store().leads.values()].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function getLead(id: string): LeadCard | undefined {
  return store().leads.get(id);
}

export function saveLead(lead: LeadCard): void {
  store().leads.set(lead.id, lead);
}

export function getSessionByPhone(phone: string): SmsSession | undefined {
  for (const s of store().sessions.values()) {
    if (s.phone === phone && s.state !== "COMPLETE" && s.state !== "OPTED_OUT") {
      return s;
    }
  }
  return undefined;
}

export function saveSession(session: SmsSession): void {
  store().sessions.set(session.id, session);
}

export function createSession(phone: string, trade: string): SmsSession {
  const session: SmsSession = {
    id: randomUUID(),
    phone,
    trade,
    state: "AWAITING_JOB_TYPE",
    notes: [],
    optedOut: false,
    updatedAt: new Date().toISOString(),
  };
  saveSession(session);
  return session;
}

export function updateLeadStatus(
  id: string,
  status: LeadCard["status"],
): LeadCard | undefined {
  const lead = store().leads.get(id);
  if (!lead) return undefined;
  const updated = { ...lead, status, updatedAt: new Date().toISOString() };
  saveLead(updated);
  return updated;
}

/** Test helper — reset in-memory state */
export function resetStore(): void {
  globalStore.__mcrStore = undefined;
}
