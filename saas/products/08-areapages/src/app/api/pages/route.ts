import { NextResponse } from "next/server";
import { listPages, seedDemoPages, isMockMode } from "@/lib/store";
import { listSuburbs } from "@/lib/suburb-data";

export async function GET() {
  let pages = listPages();
  if (pages.length === 0) {
    seedDemoPages();
    pages = listPages();
  }
  return NextResponse.json({
    pages,
    suburbs: listSuburbs(),
    mockMode: isMockMode(),
  });
}
