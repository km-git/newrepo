import { NextResponse } from "next/server";
import { getMetrics, getInsight, listQuotes, getLastSyncAt, isMockMode } from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    metrics: getMetrics(),
    insight: getInsight(),
    quotes: listQuotes(),
    lastSyncAt: getLastSyncAt(),
    mockMode: isMockMode(),
  });
}
