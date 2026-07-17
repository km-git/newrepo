import type { JobCard } from "../types";
import type { PushResult } from "../types";

export function pushToServiceM8(job: JobCard): PushResult {
  if (process.env.SERVICEM8_API_KEY) {
    // Live integration placeholder — implement OAuth + POST /job.json
    return {
      success: false,
      message: "Live ServiceM8 push not configured in MVP — set up API adapter",
    };
  }

  const externalId = `SM8-${Date.now().toString(36).toUpperCase()}`;
  console.log(
    `[MOCK ServiceM8] Created job ${externalId}: ${job.data.jobType} @ ${job.data.siteAddress}`,
  );

  return {
    success: true,
    externalId,
    message: `Job created in ServiceM8 as ${externalId}`,
  };
}
