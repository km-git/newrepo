import { NextResponse } from "next/server";
import { listSubbies, listDocuments, listPendingDocuments, getBuilderName } from "@/lib/store";
import { boardSummary } from "@/lib/compliance-board";

export async function GET() {
  const subbies = listSubbies();
  return NextResponse.json({
    builderName: getBuilderName(),
    subbies,
    documents: listDocuments(),
    pending: listPendingDocuments(),
    summary: boardSummary(subbies),
  });
}
