import { NextResponse } from "next/server";
import { syncFromServiceM8 } from "@/lib/store";

export async function POST() {
  const result = syncFromServiceM8();
  return NextResponse.json(result);
}
