import type { AreaPage, PageInput, QualityScore } from "./types";
import type { SuburbData } from "./types";
import { randomUUID } from "crypto";

export function generatePage(
  input: PageInput,
  suburb: SuburbData,
): Omit<AreaPage, "quality" | "status" | "createdAt"> {
  const title = `${input.service} in ${suburb.name} | ${input.businessName}`;
  const slug = `${input.service.toLowerCase().replace(/\s+/g, "-")}-${suburb.slug}`;
  const landmark = suburb.landmarks[0] ?? suburb.name;
  const nearby = suburb.nearbySuburbs.slice(0, 2).join(" and ");
  const jobRef =
    input.jobReferences.length > 0
      ? `Recent work includes ${input.jobReferences.join(", ")}.`
      : "";

  const intro = [
    `Looking for reliable ${input.service.toLowerCase()} in ${suburb.name}? ${input.businessName} services homes and businesses across ${suburb.name} (${suburb.postcode}) and nearby ${nearby}.`,
    `As a trusted ${input.trade.toLowerCase()} operating in the ${suburb.council} area, we understand local property types — from units near ${landmark} to family homes in surrounding streets.`,
    jobRef,
  ]
    .filter(Boolean)
    .join(" ");

  const sections = [
    {
      heading: `Why choose us for ${input.service.toLowerCase()} in ${suburb.name}?`,
      body: `We provide prompt, licensed ${input.trade.toLowerCase()} services throughout ${suburb.name} and ${suburb.nearbySuburbs.join(", ")}. Our team knows the area — including common issues in ${suburb.council} properties and access considerations near ${suburb.landmarks[1] ?? landmark}.`,
    },
    {
      heading: `Areas we service near ${suburb.name}`,
      body: `In addition to ${suburb.name}, we regularly work in ${suburb.nearbySuburbs.join(", ")} and across the ${suburb.postcode} region. Call ${input.phone} for a quote.`,
    },
    {
      heading: `Local ${input.trade.toLowerCase()} you can trust`,
      body: `${input.businessName} is committed to quality workmanship and clear communication. Whether you're near ${landmark} or on the outskirts of ${suburb.name}, we're ready to help.`,
    },
  ];

  const bodyHtml = [
    `<h1>${title}</h1>`,
    `<p>${intro}</p>`,
    ...sections.map((s) => `<h2>${s.heading}</h2><p>${s.body}</p>`),
  ].join("\n");

  const bodyText = [title, "", intro, "", ...sections.flatMap((s) => [s.heading, s.body, ""])].join(
    "\n",
  );

  const metaDescription = `${input.service} in ${suburb.name} ${suburb.postcode}. ${input.businessName} — local ${input.trade.toLowerCase()} serving ${suburb.council}. Call ${input.phone}.`;

  return {
    id: randomUUID(),
    input,
    suburb,
    title,
    metaDescription,
    slug,
    bodyHtml,
    bodyText,
  };
}

export function scorePage(page: Pick<AreaPage, "bodyText" | "suburb" | "input">, existingBodies: string[]): QualityScore {
  const warnings: string[] = [];
  const text = page.bodyText.toLowerCase();

  let localGrounding = 0;
  if (text.includes(page.suburb.name.toLowerCase())) localGrounding += 25;
  if (page.suburb.landmarks.some((l) => text.includes(l.toLowerCase()))) localGrounding += 25;
  if (page.suburb.council && text.includes(page.suburb.council.toLowerCase())) localGrounding += 20;
  if (page.input.jobReferences.some((j) => text.includes(j.toLowerCase()))) localGrounding += 15;
  localGrounding = Math.min(100, localGrounding + 15);

  let uniqueness = 100;
  for (const existing of existingBodies) {
    const similarity = jaccardSimilarity(text, existing.toLowerCase());
    if (similarity > 0.6) {
      uniqueness = Math.min(uniqueness, Math.round((1 - similarity) * 100));
      warnings.push(`High similarity (${Math.round(similarity * 100)}%) with existing page`);
    }
  }
  if (uniqueness < 70) warnings.push("Consider adding more suburb-specific details");

  const wordCount = page.bodyText.split(/\s+/).length;
  const readability = wordCount >= 150 && wordCount <= 600 ? 90 : wordCount < 100 ? 60 : 75;
  if (wordCount < 150) warnings.push("Page may be too thin for SEO — aim for 150+ words");

  const overall = Math.round((uniqueness + localGrounding + readability) / 3);

  return { uniqueness, localGrounding, readability, overall, warnings };
}

function jaccardSimilarity(a: string, b: string): number {
  const wordsA = new Set(a.split(/\W+/).filter((w) => w.length > 3));
  const wordsB = new Set(b.split(/\W+/).filter((w) => w.length > 3));
  const intersection = [...wordsA].filter((w) => wordsB.has(w)).length;
  const union = new Set([...wordsA, ...wordsB]).size;
  return union === 0 ? 0 : intersection / union;
}
