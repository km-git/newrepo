import { NextResponse } from "next/server";
import { getDigest } from "@/lib/store";

export async function GET() {
  return NextResponse.json({ digest: getDigest() });
}
