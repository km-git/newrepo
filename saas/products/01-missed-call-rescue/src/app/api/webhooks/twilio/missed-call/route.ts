import { NextResponse } from "next/server";
import { getBusiness } from "@/lib/store";
import { handleMissedCall } from "@/lib/sms-state-machine";
import { parseVoiceWebhook, sendSms } from "@/lib/twilio";

export async function POST(request: Request) {
  const form = await request.formData();
  const payload = parseVoiceWebhook(form);

  if (payload.CallStatus !== "no-answer" && payload.CallStatus !== "busy") {
    return NextResponse.json({ ok: true, skipped: true });
  }

  const biz = getBusiness();
  if (!biz) {
    return NextResponse.json({ error: "No business" }, { status: 500 });
  }

  const caller = payload.From;
  const { message } = handleMissedCall(caller, biz.trade, biz.name);

  await sendSms(caller, message);

  if (process.env.OWNER_NOTIFY_SMS === "1" && biz.ownerPhone) {
    await sendSms(
      biz.ownerPhone,
      `Missed call from ${caller}. Auto-SMS qualification started.`,
    );
  }

  return new NextResponse(
    '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    { headers: { "Content-Type": "text/xml" } },
  );
}
