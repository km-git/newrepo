import { NextResponse } from "next/server";
import {
  processEmail,
  confirmAndPush,
  rejectJob,
  updateJobData,
  getJob,
} from "@/lib/store";
import type { JobCardData, PushPlatform } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "process" | "confirm" | "reject" | "update";
    emailId?: string;
    jobId?: string;
    data?: JobCardData;
    platform?: PushPlatform;
  };

  switch (body.action) {
    case "process": {
      if (!body.emailId) {
        return NextResponse.json({ error: "emailId required" }, { status: 400 });
      }
      const job = processEmail(body.emailId);
      if (!job) {
        return NextResponse.json({ error: "Email not found" }, { status: 404 });
      }
      return NextResponse.json({ job });
    }
    case "confirm": {
      if (!body.jobId) {
        return NextResponse.json({ error: "jobId required" }, { status: 400 });
      }
      const result = confirmAndPush(body.jobId, body.platform);
      if (!result) {
        return NextResponse.json({ error: "Job not found" }, { status: 404 });
      }
      return NextResponse.json(result);
    }
    case "reject": {
      if (!body.jobId) {
        return NextResponse.json({ error: "jobId required" }, { status: 400 });
      }
      rejectJob(body.jobId);
      return NextResponse.json({ ok: true });
    }
    case "update": {
      if (!body.jobId || !body.data) {
        return NextResponse.json({ error: "jobId and data required" }, { status: 400 });
      }
      const job = updateJobData(body.jobId, body.data);
      if (!job) {
        return NextResponse.json({ error: "Invalid data or job not found" }, { status: 400 });
      }
      return NextResponse.json({ job });
    }
    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}

export async function GET(request: Request) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id) {
    return NextResponse.json({ error: "id required" }, { status: 400 });
  }
  const job = getJob(id);
  if (!job) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  return NextResponse.json({ job });
}
