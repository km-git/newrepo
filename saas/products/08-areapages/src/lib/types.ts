export type PageStatus = "draft" | "review" | "approved" | "published";

export interface SuburbData {
  slug: string;
  name: string;
  state: string;
  postcode: string;
  council: string;
  landmarks: string[];
  nearbySuburbs: string[];
}

export interface PageInput {
  businessName: string;
  service: string;
  trade: string;
  suburbSlug: string;
  jobReferences: string[];
  phone: string;
}

export interface QualityScore {
  uniqueness: number;
  localGrounding: number;
  readability: number;
  overall: number;
  warnings: string[];
}

export interface AreaPage {
  id: string;
  input: PageInput;
  suburb: SuburbData;
  title: string;
  metaDescription: string;
  slug: string;
  bodyHtml: string;
  bodyText: string;
  quality: QualityScore;
  status: PageStatus;
  wordpressPostId?: number;
  createdAt: string;
  publishedAt?: string;
}
