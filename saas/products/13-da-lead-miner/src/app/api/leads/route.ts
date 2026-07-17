import { NextResponse } from "next/server";
import {
  listLeads,
  listCouncils,
  getDigest,
  getProfile,
  getLastSyncAt,
  isMockMode,
  updateLeadStatus,
} from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    leads: listLeads(),
    councils: listCouncils(),
    digest: getDigest(),
    profile: getProfile(),
    lastSyncAt: getLastSyncAt(),
    mockMode: isMockMode(),
  });
}

export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "update_status";
    leadId: string;
    status: "new" | "reviewed" | "saved" | "dismissed";
  };

  if (body.action !== "update_status" || !body.leadId || !body.status) {
    return NextResponse.json({ error: "leadId and status required" }, { status: 400 });
  }

  const lead = updateLeadStatus(body.leadId, body.status);
  if (!lead) return NextResponse.json({ error: "Lead not found" }, { status: 404 });
  return NextResponse.json({ lead });
}
