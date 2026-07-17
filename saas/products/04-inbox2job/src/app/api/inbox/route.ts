import { NextResponse } from "next/server";
import { listEmails, listJobs, isMockMode } from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    emails: listEmails(),
    jobs: listJobs(),
    mockMode: isMockMode(),
  });
}
