import type { Review } from "./types";

export interface PostResult {
  success: boolean;
  externalId?: string;
  message: string;
}

export function postReplyToGoogle(reviewId: string, body: string): PostResult {
  if (process.env.GBP_API_KEY) {
    return { success: false, message: "Live GBP API not configured in MVP" };
  }
  const externalId = `gbp-reply-${Date.now()}`;
  console.log(`[MOCK GBP] Posted reply to review ${reviewId}: ${body.slice(0, 60)}...`);
  return {
    success: true,
    externalId,
    message: `Reply posted to Google review (${externalId})`,
  };
}

export function postReplyToFacebook(reviewId: string, body: string): PostResult {
  if (process.env.FACEBOOK_PAGE_TOKEN) {
    return { success: false, message: "Live Facebook API not configured in MVP" };
  }
  const externalId = `fb-reply-${Date.now()}`;
  console.log(`[MOCK Facebook] Posted reply to review ${reviewId}: ${body.slice(0, 60)}...`);
  return {
    success: true,
    externalId,
    message: `Reply posted to Facebook review (${externalId})`,
  };
}

export function postReply(review: Review, body: string): PostResult {
  return review.platform === "facebook"
    ? postReplyToFacebook(review.id, body)
    : postReplyToGoogle(review.id, body);
}
