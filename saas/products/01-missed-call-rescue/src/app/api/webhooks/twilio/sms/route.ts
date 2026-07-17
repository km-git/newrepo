import { NextResponse } from "next/server";
import { getBusiness } from "@/lib/store";
import { handleInboundSms } from "@/lib/sms-state-machine";
import { parseSmsWebhook, sendSms } from "@/lib/twilio";

export async function POST(request: Request) {
  const form = await request.formData();
  const payload = parseSmsWebhook(form);
  const biz = getBusiness();

  if (!biz) {
    return NextResponse.json({ error: "No business" }, { status: 500 });
  }

  const result = handleInboundSms(
    payload.From,
    payload.Body,
    biz.trade,
    biz.name,
  );

  await sendSms(payload.From, result.reply);

  if (result.notifyOwner && biz.ownerPhone) {
    const alert =
      result.lead?.urgency === "emergency"
        ? `EMERGENCY lead: ${result.lead.summary} — call ${payload.From} now`
        : `New lead: ${result.lead?.summary ?? payload.From}`;
    await sendSms(biz.ownerPhone, alert);
  }

  return new NextResponse(
    '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    { headers: { "Content-Type": "text/xml" } },
  );
}
