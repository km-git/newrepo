import { randomUUID } from "crypto";
import type { CaptureInput, FieldReport, ReportSection } from "./types";
import { getTemplate } from "./report-templates";
import { captionPhotos } from "./photo-captioner";
import { parseVoiceNotes, structureTranscript } from "./transcript-parser";

export function assembleReport(input: CaptureInput): FieldReport {
  const template = getTemplate(input.trade);
  const photos = captionPhotos(input.photoLabels);
  const voiceNotes = parseVoiceNotes(
    input.voiceTranscripts.map(structureTranscript),
    input.trade,
  );

  const sections: ReportSection[] = template.sections.map((s) => {
    const related = voiceNotes.filter((n) => n.section === s.id);
    const content =
      related.length > 0
        ? related.map((n) => `• ${n.transcript}`).join("\n")
        : `[${s.prompt} — add voice note or edit before sending]`;

    return { id: s.id, title: s.title, content };
  });

  const recommendations = voiceNotes
    .filter((n) => n.section === "recommendations")
    .map((n) => n.transcript);

  if (recommendations.length === 0) {
    recommendations.push("No additional recommendations noted at time of report.");
  }

  const completedAt = new Date().toISOString();
  const bodyText = formatReportText({
    templateName: template.name,
    input,
    sections,
    photos,
    recommendations,
    completedAt,
  });

  return {
    id: randomUUID(),
    trade: input.trade,
    jobRef: input.jobRef,
    siteAddress: input.siteAddress,
    clientName: input.clientName,
    technician: input.technician,
    completedAt,
    photos,
    voiceNotes,
    sections,
    recommendations,
    status: "draft",
    bodyText,
  };
}

function formatReportText(opts: {
  templateName: string;
  input: CaptureInput;
  sections: ReportSection[];
  photos: { label: string; caption: string }[];
  recommendations: string[];
  completedAt: string;
}): string {
  const lines = [
    opts.templateName.toUpperCase(),
    `Job ref: ${opts.input.jobRef}`,
    `Client: ${opts.input.clientName}`,
    `Site: ${opts.input.siteAddress}`,
    `Technician: ${opts.input.technician}`,
    `Completed: ${opts.completedAt}`,
    ``,
    ...opts.sections.flatMap((s) => [`## ${s.title}`, s.content, ``]),
    `## Photo Log`,
    ...opts.photos.map((p, i) => `${i + 1}. ${p.label} — ${p.caption}`),
    ``,
    `## Recommendations`,
    ...opts.recommendations.map((r) => `• ${r}`),
    ``,
    `DRAFT — Review before sending to client. Location EXIF stripped from photos.`,
  ];
  return lines.join("\n");
}
