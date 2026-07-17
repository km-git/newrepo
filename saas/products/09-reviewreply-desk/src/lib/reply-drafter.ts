import type { Review, ToneProfile, ToneStyle } from "./types";
import { shouldEscalate } from "./sentiment";

const TEMPLATES: Record<ToneStyle, { positive: string; neutral: string; negative: string }> = {
  friendly: {
    positive:
      "Thanks so much, {author}! We're stoked you had a great experience at {business}. Hope to see you again soon! {signOff}",
    neutral:
      "Thanks for your feedback, {author}. We appreciate you taking the time to review {business}. {signOff}",
    negative:
      "We're sorry to hear this, {author}. We'd like to make it right — please contact us directly so we can look into what happened. {signOff}",
  },
  professional: {
    positive:
      "Thank you for your kind review, {author}. We're pleased {business} met your expectations and look forward to serving you again. {signOff}",
    neutral:
      "Thank you for your review, {author}. Your feedback helps us improve our service at {business}. {signOff}",
    negative:
      "We apologise for your experience, {author}. Please contact {business} directly so we can address your concerns promptly. {signOff}",
  },
  warm: {
    positive:
      "What a lovely review — thank you, {author}! The whole team at {business} really appreciates your support. {signOff}",
    neutral:
      "Thank you for sharing your thoughts, {author}. We value every review at {business}. {signOff}",
    negative:
      "We're truly sorry, {author}. This isn't the experience we want for anyone. Please reach out to us — we'd love the chance to put things right. {signOff}",
  },
};

export function draftReply(review: Review, profile: ToneProfile): { body: string; escalate: boolean } {
  const template = TEMPLATES[profile.style][review.sentiment];
  const body = template
    .replace(/\{author\}/g, review.author.split(" ")[0] || "there")
    .replace(/\{business\}/g, profile.businessName)
    .replace(/\{signOff\}/g, profile.signOff);

  const escalate = profile.escalateNegative && shouldEscalate(review.sentiment, review.rating);
  return { body, escalate };
}
