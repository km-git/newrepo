import { NextResponse } from "next/server";
import {
  listChecklist,
  listEvidence,
  listCredentials,
  getProviderName,
  generateReport,
  getLastReport,
  getReportText,
} from "@/lib/store";
import { PRACTICE_STANDARDS } from "@/lib/practice-standards";

export async function GET() {
  return NextResponse.json({
    providerName: getProviderName(),
    standards: PRACTICE_STANDARDS,
    checklist: listChecklist(),
    evidence: listEvidence(),
    credentials: listCredentials(),
    lastReport: getLastReport(),
  });
}

export async function POST() {
  const report = generateReport();
  return NextResponse.json({
    report,
    text: getReportText(),
  });
}
