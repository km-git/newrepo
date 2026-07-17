import { NextResponse } from "next/server";
import { addEvidence, updateChecklistNotes } from "@/lib/store";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "add_evidence" | "update_notes";
    title?: string;
    documentRef?: string;
    standardId?: string;
    notes?: string;
  };

  switch (body.action) {
    case "add_evidence": {
      if (!body.title || !body.documentRef) {
        return NextResponse.json({ error: "title and documentRef required" }, { status: 400 });
      }
      const ev = addEvidence(body.title, body.documentRef);
      return NextResponse.json({ evidence: ev });
    }
    case "update_notes": {
      if (!body.standardId) {
        return NextResponse.json({ error: "standardId required" }, { status: 400 });
      }
      const entry = updateChecklistNotes(body.standardId, body.notes ?? "");
      return NextResponse.json({ entry });
    }
    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}
