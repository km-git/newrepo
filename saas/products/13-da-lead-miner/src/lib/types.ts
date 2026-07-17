export type WorkType =
  | "pool"
  | "renovation"
  | "extension"
  | "electrical"
  | "landscaping"
  | "demolition"
  | "other";

export type TradeFocus =
  | "builder"
  | "pool_builder"
  | "landscaper"
  | "electrician"
  | "plumber"
  | "all";

export interface Council {
  id: string;
  name: string;
  region: string;
}

export interface DevelopmentApplication {
  id: string;
  councilId: string;
  daNumber: string;
  address: string;
  suburb: string;
  description: string;
  approvedAt: string;
  workTypes: WorkType[];
  tradesNeeded: string[];
  leadScore: number;
  leadReason: string;
  status: "new" | "reviewed" | "saved" | "dismissed";
}

export interface UserProfile {
  businessName: string;
  tradeFocus: TradeFocus;
  councils: string[];
}

export interface WeeklyDigest {
  id: string;
  periodLabel: string;
  generatedAt: string;
  leadCount: number;
  topLeads: DevelopmentApplication[];
  summary: string;
}

export interface SyncResult {
  councilId: string;
  imported: number;
  mockMode: boolean;
}
