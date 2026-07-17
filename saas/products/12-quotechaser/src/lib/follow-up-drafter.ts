import type { FollowUpDraft, FollowUpStage, FollowUpTone, Quote } from "./types";
import { randomUUID } from "crypto";
import { toneForStage } from "./follow-up-cadence";

const TEMPLATES: Record<FollowUpTone, (q: Quote, biz: string, sender: string) => { subject: string; body: string }> = {
  gentle: (q, biz, sender) => ({
    subject: `Re: Quote ${q.quoteNumber} — quick check-in`,
    body: `Hi ${q.contactName.split(" ")[0]},\n\nJust checking you received our quote for ${q.jobDescription.toLowerCase()} ($${q.amountAud.toLocaleString()}). Happy to answer any questions.\n\n${sender}\n${biz}`,
  }),
  friendly: (q, biz, sender) => ({
    subject: `Following up — Quote ${q.quoteNumber}`,
    body: `Hi ${q.contactName.split(" ")[0]},\n\nWanted to follow up on the quote we sent for ${q.jobDescription.toLowerCase()}. If timing or scope needs adjusting, let me know — we can often work something out.\n\n${sender}\n${biz}`,
  }),
  firm: (q, biz, sender) => ({
    subject: `Quote ${q.quoteNumber} — still interested?`,
    body: `Hi ${q.contactName.split(" ")[0]},\n\nWe haven't heard back on quote ${q.quoteNumber} for ${q.jobDescription.toLowerCase()}. If you're still interested, reply and we'll hold the slot. Otherwise I'll close this off on our end.\n\n${sender}\n${biz}`,
  }),
};

export function draftFollowUp(
  quote: Quote,
  stage: FollowUpStage,
  businessName: string,
  senderName: string,
  sequenceId: string,
): FollowUpDraft {
  const tone = toneForStage(stage);
  const { subject, body } = TEMPLATES[tone](quote, businessName, senderName);
  return {
    id: randomUUID(),
    sequenceId,
    quoteId: quote.id,
    stage,
    tone,
    subject,
    body,
    status: "draft",
    createdAt: new Date().toISOString(),
  };
}
