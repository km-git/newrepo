/**
 * Provider-agnostic workhorse LLM adapter.
 * Mock mode by default; set WORKHORSE_LLM_URL + WORKHORSE_LLM_API_KEY for live calls.
 */

export interface WorkhorseRequest {
  system: string;
  user: string;
  maxTokens?: number;
}

export interface WorkhorseResponse {
  text: string;
  provider: "mock" | "live";
}

export async function workhorseComplete(
  req: WorkhorseRequest,
): Promise<WorkhorseResponse> {
  const url = process.env.WORKHORSE_LLM_URL;
  const key = process.env.WORKHORSE_LLM_API_KEY;

  if (url && key) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        messages: [
          { role: "system", content: req.system },
          { role: "user", content: req.user },
        ],
        max_tokens: req.maxTokens ?? 120,
      }),
    });
    if (!res.ok) {
      throw new Error(`Workhorse LLM error: ${res.status}`);
    }
    const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
    const text = data.choices?.[0]?.message?.content?.trim() ?? "";
    return { text, provider: "live" };
  }

  return { text: mockExtract(req.user), provider: "mock" };
}

/** Deterministic mock: echo structured extraction from user prompt. */
function mockExtract(user: string): string {
  const lower = user.toLowerCase();
  if (lower.includes("summarise") || lower.includes("summarize")) {
    return "Lead qualified via SMS. Customer needs help; review suburb and urgency.";
  }
  if (lower.includes("classify urgency")) {
    if (/emergency|urgent|flooding|gas leak|no power|burst/i.test(user)) return "emergency";
    if (/today|asap|this week/i.test(user)) return "soon";
    return "routine";
  }
  return "Thanks — noted.";
}
