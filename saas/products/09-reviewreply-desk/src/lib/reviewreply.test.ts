import { describe, it, expect, beforeEach } from "vitest";
import { classifySentiment, shouldEscalate } from "./sentiment";
import { draftReply } from "./reply-drafter";
import {
  resetStore,
  listReviews,
  generateDraft,
  approveAndPost,
  getProfile,
} from "./store";
import type { Review, ToneProfile } from "./types";

const profile: ToneProfile = {
  businessName: "Test Café",
  style: "friendly",
  signOff: "— Team",
  ownerName: "Sam",
  escalateNegative: true,
};

describe("sentiment", () => {
  it("classifies positive reviews", () => {
    expect(classifySentiment(5, "Amazing service, love it!")).toBe("positive");
  });

  it("classifies negative reviews", () => {
    expect(classifySentiment(1, "Terrible and rude staff")).toBe("negative");
    expect(shouldEscalate("negative", 1)).toBe(true);
  });

  it("classifies neutral reviews", () => {
    expect(classifySentiment(3, "It was fine, nothing special")).toBe("neutral");
  });
});

describe("reply-drafter", () => {
  const review: Review = {
    id: "r1",
    platform: "google",
    author: "Jane Doe",
    rating: 5,
    text: "Great!",
    locationName: "Test",
    receivedAt: new Date().toISOString(),
    sentiment: "positive",
  };

  it("drafts on-brand reply with business name", () => {
    const { body } = draftReply(review, profile);
    expect(body).toContain("Test Café");
    expect(body).toContain("Jane");
    expect(body).toContain("— Team");
  });

  it("flags escalation for negative reviews", () => {
    const neg = { ...review, rating: 1, sentiment: "negative" as const, text: "Awful" };
    const { escalate } = draftReply(neg, profile);
    expect(escalate).toBe(true);
  });
});

describe("store", () => {
  beforeEach(() => resetStore());

  it("loads demo reviews", () => {
    expect(listReviews().length).toBe(4);
  });

  it("generates draft for review", () => {
    const reviews = listReviews();
    const draft = generateDraft(reviews[0].id);
    expect(draft).toBeDefined();
    expect(draft!.body.length).toBeGreaterThan(20);
  });

  it("posts after approval", () => {
    const reviews = listReviews();
    const draft = generateDraft(reviews[0].id)!;
    const { result } = approveAndPost(draft.id)!;
    expect(result.success).toBe(true);
    expect(draft.status).toBe("posted");
  });

  it("uses warm tone from profile", () => {
    expect(getProfile().style).toBe("warm");
  });
});
