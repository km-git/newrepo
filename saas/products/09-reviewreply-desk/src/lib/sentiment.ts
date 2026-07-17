import type { ReviewSentiment } from "./types";

export function classifySentiment(rating: number, text: string): ReviewSentiment {
  const lower = text.toLowerCase();
  if (rating <= 2 || /terrible|awful|rude|never again|worst|scam|disgusting/.test(lower)) {
    return "negative";
  }
  if (rating >= 4 || /great|excellent|amazing|love|fantastic|recommend|best/.test(lower)) {
    return "positive";
  }
  return "neutral";
}

export function shouldEscalate(sentiment: ReviewSentiment, rating: number): boolean {
  return sentiment === "negative" || rating <= 2;
}
