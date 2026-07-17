import { NextResponse } from "next/server";
import { createReport, getReport, markReportReady } from "@/lib/store";
import type { CaptureInput } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json()) as
    | { action: "create"; input: CaptureInput }
    | { action: "ready"; reportId: string };

  if (body.action === "create") {
    const report = createReport(body.input);
    return NextResponse.json({ report });
  }

  if (body.action === "ready") {
    const report = markReportReady(body.reportId);
    if (!report) return NextResponse.json({ error: "Not found" }, { status: 404 });
    return NextResponse.json({ report });
  }

  return NextResponse.json({ error: "Unknown action" }, { status: 400 });
}

export async function GET(request: Request) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });
  const report = getReport(id);
  if (!report) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ report });
}
