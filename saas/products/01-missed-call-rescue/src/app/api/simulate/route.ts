import { NextResponse } from "next/server";
import { getBusiness } from "@/lib/store";
import { handleInboundSms, handleMissedCall } from "@/lib/sms-state-machine";
import { sendSms } from "@/lib/twilio";

/** Demo endpoint — simulate missed call + SMS thread without Twilio credentials */
export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "missed_call" | "sms_reply";
    phone?: string;
    message?: string;
  };

  const biz = getBusiness();
  if (!biz) {
    return NextResponse.json({ error: "No business" }, { status: 500 });
  }

  const phone = body.phone ?? "+61400111222";

  if (body.action === "missed_call") {
    const { message, session } = handleMissedCall(phone, biz.trade, biz.name);
    await sendSms(phone, message);
    return NextResponse.json({ ok: true, outbound: message, session });
  }

  if (body.action === "sms_reply") {
    const result = handleInboundSms(
      phone,
      body.message ?? "",
      biz.trade,
      biz.name,
    );
    return NextResponse.json({
      ok: true,
      reply: result.reply,
      session: result.session,
      lead: result.lead,
      notifyOwner: result.notifyOwner,
    });
  }

  return NextResponse.json({ error: "Unknown action" }, { status: 400 });
}
