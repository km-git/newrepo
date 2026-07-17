import { randomUUID } from "crypto";
import { JobCardSchema, type InboundEmail, type JobCard, type JobCardData, type PushPlatform } from "./types";
import { extractFromEmail } from "./email-extractor";
import { pushToServiceM8 } from "./adapters/servicem8";
import { pushToTradify } from "./adapters/tradify";

const globalStore = globalThis as typeof globalThis & {
  __i2jStore?: {
    emails: Map<string, InboundEmail>;
    jobs: Map<string, JobCard>;
    defaultPlatform: PushPlatform;
  };
};

const DEMO_EMAILS: InboundEmail[] = [
  {
    id: "em-001",
    from: "Sarah Mitchell <sarah.mitchell@gmail.com>",
    subject: "Blocked kitchen drain - need plumber ASAP",
    body: `Hi,

We've got a blocked kitchen drain at 42 Oak Street, Parramatta NSW 2150.
Water is backing up into the sink. Can someone come tomorrow morning?

My number is 0412 345 678.

Thanks,
Sarah Mitchell`,
    receivedAt: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "em-002",
    from: "james@buildright.com.au",
    subject: "Quote request - deck repair",
    body: `Hello,

Need a quote for deck board replacement at a property in Blacktown.
About 12sqm of boards need replacing. Not urgent - happy to wait a week.

James Chen
BuildRight Property Management
02 9876 5432`,
    receivedAt: new Date(Date.now() - 7200000).toISOString(),
  },
];

function store() {
  if (!globalStore.__i2jStore) {
    const emails = new Map(DEMO_EMAILS.map((e) => [e.id, e]));
    const jobs = new Map<string, JobCard>();
    globalStore.__i2jStore = { emails, jobs, defaultPlatform: "servicem8" };
  }
  return globalStore.__i2jStore;
}

export function listEmails(): InboundEmail[] {
  return [...store().emails.values()].sort(
    (a, b) => new Date(b.receivedAt).getTime() - new Date(a.receivedAt).getTime(),
  );
}

export function listJobs(): JobCard[] {
  return [...store().jobs.values()].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function getJob(id: string): JobCard | undefined {
  return store().jobs.get(id);
}

export function processEmail(emailId: string): JobCard | null {
  const email = store().emails.get(emailId);
  if (!email) return null;

  const { data, ambiguities } = extractFromEmail(
    email.subject,
    email.body,
    email.from,
  );

  const parsed = JobCardSchema.safeParse(data);
  const now = new Date().toISOString();

  const job: JobCard = {
    id: randomUUID(),
    emailId,
    data: parsed.success
      ? parsed.data
      : ({
          customerName: data.customerName ?? "Unknown",
          siteAddress: data.siteAddress ?? "Address TBC",
          jobType: data.jobType ?? "general enquiry",
          urgency: data.urgency ?? "routine",
          description: data.description ?? email.body.slice(0, 200),
          customerPhone: data.customerPhone,
          customerEmail: data.customerEmail,
          suburb: data.suburb,
          preferredDate: data.preferredDate,
          photoUrls: [],
        } as JobCardData),
    ambiguities: parsed.success
      ? ambiguities
      : [...ambiguities, ...parsed.error.issues.map((i) => i.message)],
    status: "pending_review",
    createdAt: now,
    updatedAt: now,
  };

  store().jobs.set(job.id, job);
  return job;
}

export function updateJobData(id: string, data: JobCardData): JobCard | null {
  const job = store().jobs.get(id);
  if (!job) return null;
  const parsed = JobCardSchema.safeParse(data);
  if (!parsed.success) return null;
  job.data = parsed.data;
  job.updatedAt = new Date().toISOString();
  return job;
}

export function confirmAndPush(
  jobId: string,
  platform?: PushPlatform,
): { job: JobCard; push: Awaited<ReturnType<typeof pushToServiceM8>> } | null {
  const job = store().jobs.get(jobId);
  if (!job || job.status === "pushed") return null;

  job.status = "confirmed";
  const target = platform ?? store().defaultPlatform;

  const push =
    target === "tradify"
      ? pushToTradify(job)
      : pushToServiceM8(job);

  if (push.success) {
    job.status = "pushed";
    job.pushPlatform = target;
    job.externalJobId = push.externalId;
  } else {
    job.status = "failed";
  }
  job.updatedAt = new Date().toISOString();
  return { job, push };
}

export function rejectJob(jobId: string): boolean {
  const job = store().jobs.get(jobId);
  if (!job) return false;
  job.status = "rejected";
  job.updatedAt = new Date().toISOString();
  return true;
}

export function ingestEmail(email: Omit<InboundEmail, "id" | "receivedAt">): InboundEmail {
  const inbound: InboundEmail = {
    ...email,
    id: randomUUID(),
    receivedAt: new Date().toISOString(),
  };
  store().emails.set(inbound.id, inbound);
  return inbound;
}

export function isMockMode(): boolean {
  return !process.env.SERVICEM8_API_KEY;
}

export function resetStore(): void {
  globalStore.__i2jStore = undefined;
}
