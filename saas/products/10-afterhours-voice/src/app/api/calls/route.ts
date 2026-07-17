import { NextResponse } from "next/server";
import { listCalls, getBusiness, getFlowVersion, isMockMode } from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    calls: listCalls(),
    business: getBusiness(),
    flowVersion: getFlowVersion(),
    mockMode: isMockMode(),
  });
}
