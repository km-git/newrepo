import { NextResponse } from "next/server";
import type { SwmsInput } from "@/lib/types";
import { buildSwms } from "@/lib/swms-builder";

export async function POST(request: Request) {
  const input = (await request.json()) as SwmsInput;
  if (!input.businessName || !input.jobDescription) {
    return NextResponse.json(
      { error: "businessName and jobDescription required" },
      { status: 400 },
    );
  }
  const doc = buildSwms(input);
  return NextResponse.json({ document: doc });
}

export async function GET() {
  return NextResponse.json({
    trades: ["electrical", "plumbing", "carpentry", "general"],
    disclaimer:
      "All outputs are drafts for PCBU review — not safety or legal advice.",
  });
}
