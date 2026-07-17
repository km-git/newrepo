import { NextResponse } from "next/server";
import {
  generateDraft,
  updateDraftBody,
  approveAndPost,
  rejectDraft,
} from "@/lib/store";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "draft" | "update" | "approve" | "reject";
    reviewId?: string;
    draftId?: string;
    replyBody?: string;
  };

  switch (body.action) {
    case "draft": {
      if (!body.reviewId) {
        return NextResponse.json({ error: "reviewId required" }, { status: 400 });
      }
      const draft = generateDraft(body.reviewId);
      if (!draft) return NextResponse.json({ error: "Review not found" }, { status: 404 });
      return NextResponse.json({ draft });
    }
    case "update": {
      if (!body.draftId || !body.replyBody) {
        return NextResponse.json({ error: "draftId and replyBody required" }, { status: 400 });
      }
      const draft = updateDraftBody(body.draftId, body.replyBody);
      if (!draft) return NextResponse.json({ error: "Draft not found" }, { status: 404 });
      return NextResponse.json({ draft });
    }
    case "approve": {
      if (!body.draftId) {
        return NextResponse.json({ error: "draftId required" }, { status: 400 });
      }
      const result = approveAndPost(body.draftId);
      if (!result) return NextResponse.json({ error: "Draft not found" }, { status: 404 });
      return NextResponse.json(result);
    }
    case "reject": {
      if (!body.draftId) {
        return NextResponse.json({ error: "draftId required" }, { status: 400 });
      }
      rejectDraft(body.draftId);
      return NextResponse.json({ ok: true });
    }
    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}
