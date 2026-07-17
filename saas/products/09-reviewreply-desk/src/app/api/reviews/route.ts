import { NextResponse } from "next/server";
import { listReviews, listDrafts, getProfile, pendingCount, isMockMode } from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    reviews: listReviews(),
    drafts: listDrafts(),
    profile: getProfile(),
    pendingCount: pendingCount(),
    mockMode: isMockMode(),
  });
}
