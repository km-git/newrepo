import { z } from "zod";

export const JobCardSchema = z.object({
  customerName: z.string().min(1, "Customer name required"),
  customerPhone: z.string().optional(),
  customerEmail: z.string().email().optional().or(z.literal("")),
  siteAddress: z.string().min(3, "Site address required"),
  suburb: z.string().optional(),
  jobType: z.string().min(2, "Job type required"),
  urgency: z.enum(["routine", "soon", "emergency"]).default("routine"),
  description: z.string().min(5, "Description required"),
  preferredDate: z.string().optional(),
  photoUrls: z.array(z.string().url()).default([]),
});

export type JobCardData = z.infer<typeof JobCardSchema>;

export type JobStatus =
  | "pending_review"
  | "confirmed"
  | "pushed"
  | "rejected"
  | "failed";

export type PushPlatform = "servicem8" | "tradify" | "simpro";

export interface InboundEmail {
  id: string;
  from: string;
  subject: string;
  body: string;
  receivedAt: string;
}

export interface JobCard {
  id: string;
  emailId: string;
  data: JobCardData;
  ambiguities: string[];
  status: JobStatus;
  pushPlatform?: PushPlatform;
  externalJobId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface PushResult {
  success: boolean;
  externalId?: string;
  message: string;
}
