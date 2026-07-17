import { NextResponse } from "next/server";
import {
  generateDraftForInvoice,
  approveDraft,
  rejectDraft,
  handleDebtorReply,
} from "@/lib/store";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "generate" | "approve" | "reject" | "classify_reply";
    invoiceId?: string;
    draftId?: string;
    replyText?: string;
  };

  switch (body.action) {
    case "generate": {
      if (!body.invoiceId) {
        return NextResponse.json({ error: "invoiceId required" }, { status: 400 });
      }
      const draft = generateDraftForInvoice(body.invoiceId);
      if (!draft) {
        return NextResponse.json({ error: "Cannot generate draft" }, { status: 400 });
      }
      return NextResponse.json({ draft });
    }
    case "approve": {
      if (!body.draftId) {
        return NextResponse.json({ error: "draftId required" }, { status: 400 });
      }
      const draft = approveDraft(body.draftId);
      if (!draft) {
        return NextResponse.json({ error: "Draft not found" }, { status: 404 });
      }
      return NextResponse.json({ draft, sent: true });
    }
    case "reject": {
      if (!body.draftId) {
        return NextResponse.json({ error: "draftId required" }, { status: 400 });
      }
      rejectDraft(body.draftId);
      return NextResponse.json({ ok: true });
    }
    case "classify_reply": {
      if (!body.invoiceId || !body.replyText) {
        return NextResponse.json(
          { error: "invoiceId and replyText required" },
          { status: 400 },
        );
      }
      const result = handleDebtorReply(body.invoiceId, body.replyText);
      return NextResponse.json(result);
    }
    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}
