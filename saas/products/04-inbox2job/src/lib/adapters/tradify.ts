import type { JobCard } from "../types";
import type { PushResult } from "../types";

export function pushToTradify(job: JobCard): PushResult {
  if (process.env.TRADIFY_API_KEY) {
    return {
      success: false,
      message: "Live Tradify push not configured in MVP",
    };
  }

  const externalId = `TRD-${Date.now().toString(36).toUpperCase()}`;
  console.log(
    `[MOCK Tradify] Created job ${externalId}: ${job.data.jobType} @ ${job.data.siteAddress}`,
  );

  return {
    success: true,
    externalId,
    message: `Job created in Tradify as ${externalId}`,
  };
}
