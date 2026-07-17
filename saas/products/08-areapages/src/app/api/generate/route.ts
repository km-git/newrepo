import { NextResponse } from "next/server";
import { createPage, approvePage, publishPage, getPage } from "@/lib/store";
import type { PageInput } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json()) as
    | { action: "create"; input: PageInput }
    | { action: "approve"; pageId: string }
    | { action: "publish"; pageId: string };

  switch (body.action) {
    case "create": {
      const page = createPage(body.input);
      if (!page) return NextResponse.json({ error: "Invalid suburb" }, { status: 400 });
      return NextResponse.json({ page });
    }
    case "approve": {
      const page = approvePage(body.pageId);
      if (!page) return NextResponse.json({ error: "Not found" }, { status: 404 });
      return NextResponse.json({ page });
    }
    case "publish": {
      const result = publishPage(body.pageId);
      if (!result) {
        return NextResponse.json({ error: "Page not approved or not found" }, { status: 400 });
      }
      return NextResponse.json(result);
    }
    default:
      return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }
}

export async function GET(request: Request) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });
  const page = getPage(id);
  if (!page) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ page });
}
