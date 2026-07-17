import type { MonthlyInsight, WinRateMetrics } from "./types";

function bestSlice(slices: WinRateMetrics["byJobType"], minDecided = 2) {
  return slices
    .filter((s) => s.won + s.lost >= minDecided)
    .sort((a, b) => b.winRate - a.winRate)[0];
}

function worstSlice(slices: WinRateMetrics["byJobType"], minDecided = 2) {
  return slices
    .filter((s) => s.won + s.lost >= minDecided)
    .sort((a, b) => a.winRate - b.winRate)[0];
}

export function generateMonthlyInsight(metrics: WinRateMetrics): MonthlyInsight {
  const { overall, byJobType, bySuburb, byResponseTime, avgResponseHours } = metrics;
  const topJob = bestSlice(byJobType);
  const weakJob = worstSlice(byJobType);
  const topSuburb = bestSlice(bySuburb);
  const fastResponse = byResponseTime.find((s) => s.key === "under_4h");
  const slowResponse = byResponseTime.find((s) => s.key === "over_24h");

  const bullets: string[] = [
    `You won ${overall.won} of ${overall.won + overall.lost} decided quotes (${overall.winRate}% win rate) worth $${overall.totalValueWon.toLocaleString()} in booked work.`,
    `Average quote response time was ${avgResponseHours} hours.`,
  ];

  if (topJob) {
    bullets.push(
      `Strongest job type: ${topJob.label} at ${topJob.winRate}% (${topJob.won}/${topJob.won + topJob.lost}).`,
    );
  }

  if (topSuburb) {
    bullets.push(`Best suburb: ${topSuburb.label} at ${topSuburb.winRate}% win rate.`);
  }

  if (fastResponse && slowResponse && fastResponse.won + fastResponse.lost > 0) {
    bullets.push(
      `Quotes answered under 4 hours won at ${fastResponse.winRate}% vs ${slowResponse.winRate}% when over 24 hours.`,
    );
  }

  const headline =
    overall.winRate >= 50
      ? `Solid month — ${overall.winRate}% win rate with clear patterns to lean into.`
      : `Win rate at ${overall.winRate}% — pricing or follow-up tweaks could lift conversions.`;

  const topOpportunity = topJob
    ? `Push more ${topJob.label} jobs in ${topSuburb?.label ?? "your best suburbs"} — you're winning ${topJob.winRate}% of these.`
    : "Send more quotes in job types where you already have a track record.";

  const caution = weakJob
    ? `${weakJob.label} is only converting at ${weakJob.winRate}% — review pricing or qualification before quoting.`
    : "Keep logging outcomes so patterns become visible.";

  return {
    period: metrics.period,
    headline,
    bullets,
    topOpportunity,
    caution,
  };
}
