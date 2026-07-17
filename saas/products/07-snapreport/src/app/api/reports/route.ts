import { NextResponse } from "next/server";
import { listReports, getBusinessName, seedDemoReport } from "@/lib/store";

export async function GET() {
  const reports = listReports();
  if (reports.length === 0) seedDemoReport();
  return NextResponse.json({
    businessName: getBusinessName(),
    reports: listReports(),
  });
}
