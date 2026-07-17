import { NextResponse } from "next/server";
import { getInsight } from "@/lib/store";

export async function GET() {
  return NextResponse.json({ insight: getInsight() });
}
