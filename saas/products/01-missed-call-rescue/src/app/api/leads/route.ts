import { NextResponse } from "next/server";
import { getBusiness, listLeads, updateLeadStatus } from "@/lib/store";
import type { LeadStatus } from "@/lib/types";

export async function GET() {
  const leads = listLeads();
  return NextResponse.json({ leads, mockMode: !process.env.TWILIO_ACCOUNT_SID });
}

export async function PATCH(request: Request) {
  const body = (await request.json()) as { id: string; status: LeadStatus };
  const lead = updateLeadStatus(body.id, body.status);
  if (!lead) {
    return NextResponse.json({ error: "Lead not found" }, { status: 404 });
  }
  return NextResponse.json({ lead });
}

export async function POST() {
  const biz = getBusiness();
  if (!biz) {
    return NextResponse.json({ error: "No business configured" }, { status: 500 });
  }
  return NextResponse.json({ business: biz });
}
