import type { Invoice, ReminderDraft, ReminderTone, BusinessSettings } from "./types";
import { toneForStage } from "./escalation-ladder";
import type { ChaseStage } from "./types";
import { randomUUID } from "crypto";

const TONE_TEMPLATES: Record<
  ReminderTone,
  { subject: string; body: (inv: Invoice, biz: BusinessSettings) => string }
> = {
  friendly: {
    subject: "Quick reminder — invoice {number}",
    body: (inv, biz) =>
      `Hi ${inv.contactName},\n\n` +
      `Hope you're well. Just a friendly reminder that invoice ${inv.invoiceNumber} for ` +
      `$${inv.amountDue.toFixed(2)} was due on ${inv.dueDate}.\n\n` +
      `If you've already paid, please ignore this — and thanks! ` +
      `Otherwise we'd appreciate payment when you get a chance.\n\n` +
      `Cheers,\n${biz.senderName}\n${biz.businessName}`,
  },
  firm: {
    subject: "Payment overdue — invoice {number}",
    body: (inv, biz) =>
      `Hi ${inv.contactName},\n\n` +
      `Invoice ${inv.invoiceNumber} for $${inv.amountDue.toFixed(2)} is now ` +
      `${inv.daysOverdue} days overdue (due ${inv.dueDate}).\n\n` +
      `Please arrange payment this week, or reply if there's an issue we should know about.\n\n` +
      `Regards,\n${biz.senderName}\n${biz.businessName}`,
  },
  final: {
    subject: "Final reminder — invoice {number} action required",
    body: (inv, biz) =>
      `Hi ${inv.contactName},\n\n` +
      `This is a final reminder regarding invoice ${inv.invoiceNumber} for ` +
      `$${inv.amountDue.toFixed(2)}, now ${inv.daysOverdue} days overdue.\n\n` +
      `Please pay promptly or contact us to discuss. We may need to pause further work ` +
      `until the account is brought up to date.\n\n` +
      `Note: This is a payment reminder only, not a debt collection notice.\n\n` +
      `${biz.senderName}\n${biz.businessName}`,
  },
};

export function draftReminder(
  invoice: Invoice,
  stage: ChaseStage,
  settings: BusinessSettings,
  sequenceId: string,
): ReminderDraft {
  const tone = toneForStage(stage);
  const template = TONE_TEMPLATES[tone];
  const now = new Date().toISOString();

  return {
    id: randomUUID(),
    sequenceId,
    invoiceId: invoice.id,
    stage,
    tone,
    channel: "email",
    subject: template.subject.replace("{number}", invoice.invoiceNumber),
    body: template.body(invoice, settings),
    status: "draft",
    createdAt: now,
  };
}
