import { NextResponse } from "next/server";
import { syncAllCouncils, syncCouncil } from "@/lib/store";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as { councilId?: string };
  if (body.councilId) {
    return NextResponse.json(syncCouncil(body.councilId));
  }
  return NextResponse.json({ results: syncAllCouncils() });
}
