import { describe, it, expect, beforeEach } from "vitest";
import { extractFromEmail } from "./email-extractor";
import { JobCardSchema } from "./types";
import {
  resetStore,
  processEmail,
  confirmAndPush,
  listEmails,
  ingestEmail,
} from "./store";

describe("email-extractor", () => {
  it("extracts plumber enquiry with address and phone", () => {
    const { data, ambiguities } = extractFromEmail(
      "Blocked kitchen drain - need plumber",
      `We've got a blocked kitchen drain at 42 Oak Street, Parramatta NSW 2150.
Water backing up. Can someone come tomorrow morning?
My number is 0412 345 678.
Thanks, Sarah Mitchell`,
      "Sarah Mitchell <sarah@gmail.com>",
    );

    expect(data.customerName).toBe("Sarah Mitchell");
    expect(data.customerPhone).toContain("0412");
    expect(data.siteAddress).toMatch(/42 Oak Street/i);
    expect(data.suburb).toBe("Parramatta");
    expect(data.jobType).toMatch(/plumb/i);
    expect(data.urgency).toBe("soon");
    expect(ambiguities.length).toBeLessThanOrEqual(1);
  });

  it("flags ambiguous job type", () => {
    const { ambiguities } = extractFromEmail(
      "Hello",
      "Just wondering if you're available sometime.",
      "someone@example.com",
    );
    expect(ambiguities.some((a) => a.includes("Job type"))).toBe(true);
  });

  it("detects emergency urgency", () => {
    const { data } = extractFromEmail(
      "URGENT no power",
      "We have no power at 10 Main Road, urgent emergency",
      "bob@test.com",
    );
    expect(data.urgency).toBe("emergency");
  });
});

describe("job workflow", () => {
  beforeEach(() => resetStore());

  it("processes demo email into pending job card", () => {
    const emails = listEmails();
    const job = processEmail(emails[0].id);
    expect(job).toBeDefined();
    expect(job!.status).toBe("pending_review");
    expect(job!.data.customerName).toBeTruthy();
  });

  it("validates job card schema", () => {
    const emails = listEmails();
    const job = processEmail(emails[0].id);
    const result = JobCardSchema.safeParse(job!.data);
    expect(result.success).toBe(true);
  });

  it("pushes to ServiceM8 after confirm", () => {
    const emails = listEmails();
    const job = processEmail(emails[0].id)!;
    const { push } = confirmAndPush(job.id)!;
    expect(push.success).toBe(true);
    expect(push.externalId).toMatch(/^SM8-/);
  });

  it("ingests new email and processes", () => {
    const email = ingestEmail({
      from: "test@example.com",
      subject: "Leaking tap at 5 River Road, Penrith",
      body: "Hi, leaking kitchen tap needs fixing. Call 0400 111 222. Thanks, Mike",
    });
    const job = processEmail(email.id);
    expect(job!.data.jobType).toMatch(/plumb/i);
  });
});
