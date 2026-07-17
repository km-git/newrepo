import { NextResponse } from "next/server";
import {
  listInvoices,
  listPendingDrafts,
  listAllDrafts,
  isMockMode,
  getSettings,
} from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    invoices: listInvoices(),
    pendingDrafts: listPendingDrafts(),
    allDrafts: listAllDrafts(),
    settings: getSettings(),
    mockMode: isMockMode(),
  });
}
