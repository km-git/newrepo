export type TradeTemplate = "electrical" | "pest" | "solar" | "maintenance";

export type ReportStatus = "draft" | "ready" | "sent";

export interface PhotoItem {
  id: string;
  label: string;
  caption: string;
  exifStripped: boolean;
}

export interface VoiceNote {
  id: string;
  transcript: string;
  section?: string;
}

export interface FieldReport {
  id: string;
  trade: TradeTemplate;
  jobRef: string;
  siteAddress: string;
  clientName: string;
  technician: string;
  completedAt: string;
  photos: PhotoItem[];
  voiceNotes: VoiceNote[];
  sections: ReportSection[];
  recommendations: string[];
  status: ReportStatus;
  bodyText: string;
}

export interface ReportSection {
  id: string;
  title: string;
  content: string;
}

export interface CaptureInput {
  trade: TradeTemplate;
  jobRef: string;
  siteAddress: string;
  clientName: string;
  technician: string;
  photoLabels: string[];
  voiceTranscripts: string[];
}
