import { randomUUID } from "crypto";
import type { ComplianceDocument, Subcontractor, DocumentType } from "./types";
import { DOC_LABELS } from "./types";
import { detectDocumentType, parseCertificate } from "./cert-parser";
import { computeSubbieCompliance } from "./compliance-board";

const globalStore = globalThis as typeof globalThis & {
  __scStore?: {
    builderName: string;
    subbies: Map<string, Subcontractor>;
    documents: Map<string, ComplianceDocument>;
  };
};

function refreshSubbieCompliance(subbieId: string) {
  const subbie = store().subbies.get(subbieId);
  if (!subbie) return;
  const result = computeSubbieCompliance(subbieId, listDocuments());
  Object.assign(subbie, result);
}

function store() {
  if (!globalStore.__scStore) {
    const subbies = new Map<string, Subcontractor>([
      [
        "sub-001",
        {
          id: "sub-001",
          companyName: "Ace Electrical Pty Ltd",
          contactName: "Mike Torres",
          contactEmail: "mike@aceelectrical.com.au",
          trade: "Electrical",
          compliance: "expiring",
          missingDocs: [],
          expiringDocs: [],
        },
      ],
      [
        "sub-002",
        {
          id: "sub-002",
          companyName: "Quick Plumbing Co",
          contactName: "Lisa Chen",
          contactEmail: "lisa@quickplumb.com.au",
          trade: "Plumbing",
          compliance: "non_compliant",
          missingDocs: ["workers_comp"],
          expiringDocs: [],
        },
      ],
      [
        "sub-003",
        {
          id: "sub-003",
          companyName: "Solid Form Concreting",
          contactName: "Dave Morrison",
          contactEmail: "dave@solidform.com.au",
          trade: "Concreting",
          compliance: "compliant",
          missingDocs: [],
          expiringDocs: [],
        },
      ],
    ]);

    const documents = new Map<string, ComplianceDocument>();

    const demoDocs: { subbieId: string; fileName: string; text: string; confirmed: boolean }[] = [
      {
        subbieId: "sub-001",
        fileName: "Public_Liability_Insurance_2026.pdf",
        text: "Public Liability Insurance. Insurer: QBE Insurance. Policy: PL-8844221. Coverage $20 million. Expiry: 15/08/2026",
        confirmed: true,
      },
      {
        subbieId: "sub-001",
        fileName: "Electrical_Licence_NSW.pdf",
        text: "Contractor Licence NSW. Licence: EL123456. Expires 01/09/2026",
        confirmed: true,
      },
      {
        subbieId: "sub-002",
        fileName: "PLI_Certificate.pdf",
        text: "Public liability. Policy REF-99112. $10 million. Valid until 2027-03-01",
        confirmed: true,
      },
    ];

    for (const d of demoDocs) {
      const doc = createDocumentFromText(d.subbieId, d.fileName, d.text);
      if (d.confirmed) {
        doc.status = "confirmed";
        doc.confirmedAt = new Date().toISOString();
      }
      documents.set(doc.id, doc);
    }

    globalStore.__scStore = { builderName: "Demo Construction Group", subbies, documents };

    for (const id of subbies.keys()) refreshSubbieCompliance(id);
  }
  return globalStore.__scStore;
}

function createDocumentFromText(
  subbieId: string,
  fileName: string,
  rawText: string,
): ComplianceDocument {
  const documentType = detectDocumentType(fileName, rawText);
  return {
    id: randomUUID(),
    subbieId,
    documentType,
    fileName,
    uploadedAt: new Date().toISOString(),
    parsed: parseCertificate(fileName, rawText),
    status: "pending_review",
  };
}

export function getBuilderName(): string {
  return store().builderName;
}

export function listSubbies(): Subcontractor[] {
  return [...store().subbies.values()];
}

export function getSubbie(id: string): Subcontractor | undefined {
  return store().subbies.get(id);
}

export function listDocuments(subbieId?: string): ComplianceDocument[] {
  const docs = [...store().documents.values()];
  return subbieId ? docs.filter((d) => d.subbieId === subbieId) : docs;
}

export function listPendingDocuments(): ComplianceDocument[] {
  return listDocuments().filter((d) => d.status === "pending_review");
}

export function uploadDocument(
  subbieId: string,
  fileName: string,
  rawText: string,
): ComplianceDocument | null {
  if (!store().subbies.has(subbieId)) return null;
  const doc = createDocumentFromText(subbieId, fileName, rawText);
  store().documents.set(doc.id, doc);
  return doc;
}

export function confirmDocument(docId: string, overrides?: Partial<ComplianceDocument["parsed"]>): ComplianceDocument | null {
  const doc = store().documents.get(docId);
  if (!doc) return null;
  doc.parsed = { ...doc.parsed, ...overrides };
  doc.status = "confirmed";
  doc.confirmedAt = new Date().toISOString();
  refreshSubbieCompliance(doc.subbieId);
  return doc;
}

export function rejectDocument(docId: string): boolean {
  const doc = store().documents.get(docId);
  if (!doc) return false;
  doc.status = "rejected";
  return true;
}

export function resetStore(): void {
  globalStore.__scStore = undefined;
}

export { DOC_LABELS };
export type { DocumentType };
