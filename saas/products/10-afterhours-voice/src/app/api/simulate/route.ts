import { NextResponse } from "next/server";
import { answerCall, purgeRecording } from "@/lib/telephony-adapter";
import { getBusiness, saveSession, saveCall, getSession } from "@/lib/store";
import { startSession, processUtterance } from "@/lib/voice-state-machine";

/** Simulated after-hours call harness — no Twilio credentials required */
export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "start" | "utterance" | "purge";
    phone?: string;
    sessionId?: string;
    utterance?: string;
    callId?: string;
  };

  const biz = getBusiness();

  switch (body.action) {
    case "start": {
      const phone = body.phone ?? "+61400999888";
      answerCall(phone);
      const session = startSession(phone, biz);
      saveSession(session);
      const greeting = session.transcript[0]?.text ?? "";
      return NextResponse.json({ session, greeting });
    }

    case "utterance": {
      if (!body.sessionId || !body.utterance) {
        return NextResponse.json(
          { error: "sessionId and utterance required" },
          { status: 400 },
        );
      }
      const session = getSession(body.sessionId);
      if (!session) {
        return NextResponse.json({ error: "Session not found" }, { status: 404 });
      }
      const result = processUtterance(session, body.utterance, biz);
      saveSession(result.session);
      if (result.callRecord) {
        const purged = purgeRecording(result.callRecord.id);
        result.callRecord.recordingPurgedAt = purged.purgedAt;
        saveCall(result.callRecord);
      }
      return NextResponse.json({
        reply: result.reply,
        session: result.session,
        escalated: result.escalated,
        escalationSms: result.escalationSms,
        callRecord: result.callRecord,
      });
    }

    case "purge": {
      if (!body.callId) {
        return NextResponse.json({ error: "callId required" }, { status: 400 });
      }
      const purged = purgeRecording(body.callId);
      return NextResponse.json({ ok: true, ...purged });
    }

    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}
