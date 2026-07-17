import { NextResponse } from "next/server";
import {
  uploadDocument,
  confirmDocument,
  rejectDocument,
  getSubbie,
  listDocuments,
} from "@/lib/store";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    action: "upload" | "confirm" | "reject";
    subbieId?: string;
    docId?: string;
    fileName?: string;
    rawText?: string;
    overrides?: Record<string, string>;
  };

  switch (body.action) {
    case "upload": {
      if (!body.subbieId || !body.fileName || !body.rawText) {
        return NextResponse.json({ error: "subbieId, fileName, rawText required" }, { status: 400 });
      }
      const doc = uploadDocument(body.subbieId, body.fileName, body.rawText);
      if (!doc) return NextResponse.json({ error: "Subbie not found" }, { status: 404 });
      return NextResponse.json({ document: doc });
    }
    case "confirm": {
      if (!body.docId) {
        return NextResponse.json({ error: "docId required" }, { status: 400 });
      }
      const doc = confirmDocument(body.docId, body.overrides);
      if (!doc) return NextResponse.json({ error: "Document not found" }, { status: 404 });
      return NextResponse.json({ document: doc });
    }
    case "reject": {
      if (!body.docId) {
        return NextResponse.json({ error: "docId required" }, { status: 400 });
      }
      rejectDocument(body.docId);
      return NextResponse.json({ ok: true });
    }
    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}

export async function GET(request: Request) {
  const subbieId = new URL(request.url).searchParams.get("subbieId");
  if (!subbieId) {
    return NextResponse.json({ error: "subbieId required" }, { status: 400 });
  }
  const subbie = getSubbie(subbieId);
  if (!subbie) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ subbie, documents: listDocuments(subbieId) });
}
