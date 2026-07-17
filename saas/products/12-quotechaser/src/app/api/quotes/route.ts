import { NextResponse } from "next/server";
import {
  listQuotes,
  listStaleQuotes,
  listDrafts,
  getSettings,
  pendingCount,
  isMockMode,
} from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    quotes: listQuotes(),
    stale: listStaleQuotes(),
    drafts: listDrafts(),
    settings: getSettings(),
    pendingCount: pendingCount(),
    mockMode: isMockMode(),
  });
}
