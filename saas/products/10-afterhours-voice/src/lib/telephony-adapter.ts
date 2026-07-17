import type { BusinessProfile } from "./types";

export interface SmsResult {
  success: boolean;
  messageId: string;
  message: string;
}

export function sendEscalationSms(
  biz: BusinessProfile,
  body: string,
): SmsResult {
  if (process.env.TWILIO_ACCOUNT_SID) {
    return { success: false, messageId: "", message: "Live Twilio not configured in MVP" };
  }
  const messageId = `mock-sms-${Date.now()}`;
  console.log(`[MOCK SMS] To ${biz.onCallPhone}: ${body}`);
  return {
    success: true,
    messageId,
    message: `Escalation SMS sent to on-call (${messageId})`,
  };
}

export function purgeRecording(callId: string): { purgedAt: string } {
  const purgedAt = new Date().toISOString();
  console.log(`[MOCK] Recording purged for call ${callId} at ${purgedAt}`);
  return { purgedAt };
}

export function answerCall(callerPhone: string): { callSid: string } {
  const callSid = `mock-call-${Date.now()}`;
  console.log(`[MOCK] Answered after-hours call from ${callerPhone} (${callSid})`);
  return { callSid };
}
