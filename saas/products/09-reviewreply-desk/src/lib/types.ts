export type ReviewSentiment = "positive" | "neutral" | "negative";

export type ReviewPlatform = "google" | "facebook";

export type ReplyStatus = "pending_draft" | "pending_approval" | "approved" | "posted" | "rejected";

export type ToneStyle = "friendly" | "professional" | "warm";

export interface ToneProfile {
  businessName: string;
  style: ToneStyle;
  signOff: string;
  ownerName: string;
  escalateNegative: boolean;
}

export interface Review {
  id: string;
  platform: ReviewPlatform;
  author: string;
  rating: number;
  text: string;
  locationName: string;
  receivedAt: string;
  sentiment: ReviewSentiment;
}

export interface ReplyDraft {
  id: string;
  reviewId: string;
  body: string;
  status: ReplyStatus;
  tone: ToneStyle;
  escalate: boolean;
  createdAt: string;
  postedAt?: string;
}
