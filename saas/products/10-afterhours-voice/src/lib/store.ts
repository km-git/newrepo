import type { BusinessProfile, CallRecord, VoiceSession } from "./types";
import { FLOW_VERSION } from "./call-flow";

const globalStore = globalThis as typeof globalThis & {
  __ahvStore?: {
    business: BusinessProfile;
    sessions: Map<string, VoiceSession>;
    calls: Map<string, CallRecord>;
    flowVersion: string;
  };
};

const DEMO_BUSINESS: BusinessProfile = {
  id: "demo-plumber",
  name: "RapidFlow Plumbing",
  trade: "plumber",
  afterHoursNumber: "+61290001111",
  onCallPhone: "+61400111222",
  hoursStart: "17:00",
  hoursEnd: "07:00",
  emergency: {
    keywords: ["flooding", "burst", "gas", "sewage", "no water"],
    escalateUrgencies: ["emergency"],
  },
};

function store() {
  if (!globalStore.__ahvStore) {
    globalStore.__ahvStore = {
      business: DEMO_BUSINESS,
      sessions: new Map(),
      calls: new Map(),
      flowVersion: FLOW_VERSION,
    };
  }
  return globalStore.__ahvStore;
}

export function getBusiness(): BusinessProfile {
  return store().business;
}

export function getFlowVersion(): string {
  return store().flowVersion;
}

export function saveSession(session: VoiceSession): void {
  store().sessions.set(session.id, session);
}

export function getSession(id: string): VoiceSession | undefined {
  return store().sessions.get(id);
}

export function listCalls(): CallRecord[] {
  return [...store().calls.values()].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function saveCall(record: CallRecord): void {
  store().calls.set(record.id, record);
}

export function pendingEscalations(): number {
  return listCalls().filter((c) => c.escalated).length;
}

export function isMockMode(): boolean {
  return !process.env.TWILIO_ACCOUNT_SID;
}

export function resetStore(): void {
  globalStore.__ahvStore = undefined;
}
