export interface SendResult {
  success: boolean;
  messageId: string;
  message: string;
}

export function sendFollowUpEmail(
  to: string,
  subject: string,
  body: string,
): SendResult {
  if (process.env.GMAIL_CLIENT_ID || process.env.MICROSOFT_GRAPH_TOKEN) {
    return { success: false, messageId: "", message: "Live email API not configured in MVP" };
  }
  const messageId = `mock-email-${Date.now()}`;
  console.log(`[MOCK EMAIL] To ${to}: ${subject} — ${body.slice(0, 50)}...`);
  return {
    success: true,
    messageId,
    message: `Follow-up sent (${messageId})`,
  };
}
