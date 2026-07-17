export interface TwilioSmsPayload {
  To: string;
  From: string;
  Body: string;
}

export interface TwilioVoicePayload {
  To: string;
  From: string;
  CallStatus: string;
}

const MOCK_MODE =
  !process.env.TWILIO_ACCOUNT_SID || !process.env.TWILIO_AUTH_TOKEN;

export function isMockMode(): boolean {
  return MOCK_MODE;
}

export async function sendSms(to: string, body: string): Promise<{ sid: string }> {
  if (MOCK_MODE) {
    console.log(`[MOCK SMS] to=${to} body=${body.slice(0, 80)}...`);
    return { sid: `mock_${Date.now()}` };
  }

  const accountSid = process.env.TWILIO_ACCOUNT_SID!;
  const authToken = process.env.TWILIO_AUTH_TOKEN!;
  const from = process.env.TWILIO_PHONE_NUMBER!;

  const params = new URLSearchParams({ To: to, From: from, Body: body });
  const res = await fetch(
    `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`,
    {
      method: "POST",
      headers: {
        Authorization:
          "Basic " + Buffer.from(`${accountSid}:${authToken}`).toString("base64"),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    },
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Twilio SMS failed: ${res.status} ${err}`);
  }

  const data = (await res.json()) as { sid: string };
  return { sid: data.sid };
}

export function parseSmsWebhook(
  form: FormData | Record<string, string>,
): TwilioSmsPayload {
  const get = (k: string) =>
    form instanceof FormData ? (form.get(k) as string) : form[k];

  return {
    To: get("To") ?? "",
    From: get("From") ?? "",
    Body: get("Body") ?? "",
  };
}

export function parseVoiceWebhook(
  form: FormData | Record<string, string>,
): TwilioVoicePayload {
  const get = (k: string) =>
    form instanceof FormData ? (form.get(k) as string) : form[k];

  return {
    To: get("To") ?? "",
    From: get("From") ?? "",
    CallStatus: get("CallStatus") ?? "",
  };
}
