import { randomUUID } from "crypto";
import type { PhotoItem } from "./types";

const CAPTION_TEMPLATES: Record<string, string> = {
  switchboard: "Switchboard area — work completed as scoped",
  panel: "Solar panel array installation on roof",
  inverter: "Inverter unit mounted and connected",
  roof: "Roof penetration and weatherproofing detail",
  meter: "Meter box and supply connection point",
  treatment: "Treatment area — product applied per label",
  damage: "Evidence of damage or pest activity documented",
  before: "Before condition — prior to work commencing",
  after: "After condition — work completed",
  test: "Testing equipment reading captured on site",
  default: "Site photo documenting completed work",
};

export function captionPhoto(label: string): PhotoItem {
  const lower = label.toLowerCase();
  let caption = CAPTION_TEMPLATES.default;

  for (const [key, template] of Object.entries(CAPTION_TEMPLATES)) {
    if (key !== "default" && lower.includes(key)) {
      caption = template;
      break;
    }
  }

  return {
    id: randomUUID(),
    label,
    caption,
    exifStripped: true,
  };
}

export function captionPhotos(labels: string[]): PhotoItem[] {
  return labels.map(captionPhoto);
}
