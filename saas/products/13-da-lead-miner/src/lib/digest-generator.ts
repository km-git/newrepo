import type { DevelopmentApplication, WeeklyDigest } from "./types";
import { randomUUID } from "crypto";
import { scoreLabel } from "./lead-scorer";

export function generateWeeklyDigest(leads: DevelopmentApplication[]): WeeklyDigest {
  const sorted = [...leads]
    .filter((l) => l.status !== "dismissed")
    .sort((a, b) => b.leadScore - a.leadScore);

  const topLeads = sorted.slice(0, 5);
  const hot = sorted.filter((l) => scoreLabel(l.leadScore) === "hot").length;

  const suburbs = [...new Set(topLeads.map((l) => l.suburb))];
  const summary =
    topLeads.length === 0
      ? "No new DA leads matched your filters this week."
      : `${sorted.length} new approvals across ${suburbs.length} suburb(s). ${hot} hot lead(s) match your trade focus — pool and extension work dominating this week.`;

  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 86400000);

  return {
    id: randomUUID(),
    periodLabel: `${weekAgo.toLocaleDateString("en-AU")} – ${now.toLocaleDateString("en-AU")}`,
    generatedAt: now.toISOString(),
    leadCount: sorted.length,
    topLeads,
    summary,
  };
}
