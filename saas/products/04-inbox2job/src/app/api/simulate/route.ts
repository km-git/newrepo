import { NextResponse } from "next/server";
import { ingestEmail, processEmail } from "@/lib/store";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    from: string;
    subject: string;
    body: string;
    autoProcess?: boolean;
  };

  const email = ingestEmail({
    from: body.from,
    subject: body.subject,
    body: body.body,
  });

  const job = body.autoProcess !== false ? processEmail(email.id) : null;

  return NextResponse.json({ email, job });
}
