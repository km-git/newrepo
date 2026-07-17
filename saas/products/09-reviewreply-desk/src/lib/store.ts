import { randomUUID } from "crypto";
import type { Review, ReplyDraft, ToneProfile } from "./types";
import { classifySentiment } from "./sentiment";
import { draftReply } from "./reply-drafter";
import { postReply } from "./gbp-adapter";

const globalStore = globalThis as typeof globalThis & {
  __rrdStore?: {
    profile: ToneProfile;
    reviews: Map<string, Review>;
    drafts: Map<string, ReplyDraft>;
  };
};

const DEMO_REVIEWS: Omit<Review, "sentiment">[] = [
  {
    id: "rev-001",
    platform: "google",
    author: "Sarah M.",
    rating: 5,
    text: "Amazing coffee and friendly staff! Best café in Parramatta.",
    locationName: "Bean & Brew Parramatta",
    receivedAt: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "rev-002",
    platform: "google",
    author: "James T.",
    rating: 3,
    text: "Food was okay but waited 25 minutes for a table on Saturday.",
    locationName: "Bean & Brew Parramatta",
    receivedAt: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: "rev-003",
    platform: "facebook",
    author: "Michelle K.",
    rating: 1,
    text: "Terrible service. Staff were rude and my order was wrong.",
    locationName: "Bean & Brew Parramatta",
    receivedAt: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: "rev-004",
    platform: "google",
    author: "David L.",
    rating: 5,
    text: "Love the new menu! Great atmosphere for working remotely.",
    locationName: "Bean & Brew Parramatta",
    receivedAt: new Date(Date.now() - 14400000).toISOString(),
  },
];

function store() {
  if (!globalStore.__rrdStore) {
    const reviews = new Map<string, Review>();
    const drafts = new Map<string, ReplyDraft>();

    for (const r of DEMO_REVIEWS) {
      reviews.set(r.id, { ...r, sentiment: classifySentiment(r.rating, r.text) });
    }

    globalStore.__rrdStore = {
      profile: {
        businessName: "Bean & Brew",
        style: "warm",
        signOff: "— The Bean & Brew Team",
        ownerName: "Alex",
        escalateNegative: true,
      },
      reviews,
      drafts,
    };
  }
  return globalStore.__rrdStore;
}

export function getProfile(): ToneProfile {
  return store().profile;
}

export function listReviews(): Review[] {
  return [...store().reviews.values()].sort(
    (a, b) => new Date(b.receivedAt).getTime() - new Date(a.receivedAt).getTime(),
  );
}

export function getReview(id: string): Review | undefined {
  return store().reviews.get(id);
}

export function listDrafts(): ReplyDraft[] {
  return [...store().drafts.values()];
}

export function getDraftForReview(reviewId: string): ReplyDraft | undefined {
  return [...store().drafts.values()].find((d) => d.reviewId === reviewId);
}

export function generateDraft(reviewId: string): ReplyDraft | null {
  const review = store().reviews.get(reviewId);
  if (!review) return null;

  const existing = getDraftForReview(reviewId);
  if (existing) return existing;

  const { body, escalate } = draftReply(review, store().profile);
  const draft: ReplyDraft = {
    id: randomUUID(),
    reviewId,
    body,
    status: escalate ? "pending_approval" : "pending_approval",
    tone: store().profile.style,
    escalate,
    createdAt: new Date().toISOString(),
  };
  store().drafts.set(draft.id, draft);
  return draft;
}

export function updateDraftBody(draftId: string, body: string): ReplyDraft | null {
  const draft = store().drafts.get(draftId);
  if (!draft) return null;
  draft.body = body;
  return draft;
}

export function approveAndPost(draftId: string): { draft: ReplyDraft; result: ReturnType<typeof postReply> } | null {
  const draft = store().drafts.get(draftId);
  const review = draft ? store().reviews.get(draft.reviewId) : undefined;
  if (!draft || !review) return null;

  draft.status = "approved";
  const result = postReply(review, draft.body);
  if (result.success) {
    draft.status = "posted";
    draft.postedAt = new Date().toISOString();
  }
  return { draft, result };
}

export function rejectDraft(draftId: string): boolean {
  const draft = store().drafts.get(draftId);
  if (!draft) return false;
  draft.status = "rejected";
  return true;
}

export function pendingCount(): number {
  return listDrafts().filter((d) => d.status === "pending_approval").length;
}

export function isMockMode(): boolean {
  return !process.env.GBP_API_KEY;
}

export function resetStore(): void {
  globalStore.__rrdStore = undefined;
}
