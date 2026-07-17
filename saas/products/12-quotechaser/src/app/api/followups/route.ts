import { NextResponse } from "next/server";
import {
  generateDraft,
  updateDraftBody,
  approveAndSend,
  rejectDraft,
} from "@/lib/store";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "draft" | "update" | "approve" | "reject";
    quoteId?: string;
    draftId?: string;
    subject?: string;
    body?: string;
  };

  switch (body.action) {
    case "draft": {
      if (!body.quoteId) {
        return NextResponse.json({ error: "quoteId required" }, { status: 400 });
      }
      const draft = generateDraft(body.quoteId);
      if (!draft) {
        return NextResponse.json({ error: "Quote not eligible for follow-up" }, { status: 404 });
      }
      return NextResponse.json({ draft });
    }
    case "update": {
      if (!body.draftId || !body.subject || !body.body) {
        return NextResponse.json({ error: "draftId, subject, body required" }, { status: 400 });
      }
      const draft = updateDraftBody(body.draftId, body.subject, body.body);
      if (!draft) return NextResponse.json({ error: "Draft not found" }, { status: 404 });
      return NextResponse.json({ draft });
    }
    case "approve": {
      if (!body.draftId) {
        return NextResponse.json({ error: "draftId required" }, { status: 400 });
      }
      const result = approveAndSend(body.draftId);
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
