import type { HazardControl, Trade } from "./types";

export const HAZARD_LIBRARY: Record<Trade, HazardControl[]> = {
  electrical: [
    {
      id: "elec-live",
      hazard: "Contact with live electrical parts",
      risk: "Electric shock, burns, fatality",
      controls: [
        "Isolate and lock out/tag out before work",
        "Test before touch with approved tester",
        "Use insulated tools rated for voltage",
      ],
      ppe: ["Insulated gloves", "Safety glasses", "Arc-rated clothing where required"],
    },
    {
      id: "elec-height",
      hazard: "Working at height (ladders, EWP)",
      risk: "Falls causing serious injury",
      controls: [
        "Use 3-point contact on ladders",
        "Inspect EWP pre-start; use harness where required",
        "Barricade work area below",
      ],
      ppe: ["Hard hat", "Harness if required", "Non-slip footwear"],
    },
    {
      id: "elec-manual",
      hazard: "Manual handling of cables and equipment",
      risk: "Musculoskeletal injury",
      controls: [
        "Team lift items over 20kg",
        "Use mechanical aids where practical",
        "Clear trip hazards in work area",
      ],
      ppe: ["Gloves"],
    },
  ],
  plumbing: [
    {
      id: "plumb-confined",
      hazard: "Confined spaces (roof void, pits)",
      risk: "Asphyxiation, entrapment",
      controls: [
        "Assess space before entry; use permit if required",
        "Maintain communication with spotter",
        "Never enter alone",
      ],
      ppe: ["Hard hat", "Torch", "Respirator if atmosphere risk"],
    },
    {
      id: "plumb-hot",
      hazard: "Hot works / soldering / cutting",
      risk: "Burns, fire",
      controls: [
        "Fire extinguisher within 5m",
        "Hot work permit where site requires",
        "Clear combustibles; monitor 30 min post-work",
      ],
      ppe: ["Heat-resistant gloves", "Safety glasses"],
    },
    {
      id: "plumb-slip",
      hazard: "Slips from water and waste",
      risk: "Falls, contamination",
      controls: [
        "Contain spills immediately",
        "Use signage for wet areas",
        "Dispose of waste per site rules",
      ],
      ppe: ["Gloves", "Waterproof boots"],
    },
  ],
  carpentry: [
    {
      id: "carp-power",
      hazard: "Power tools (saws, nail guns)",
      risk: "Laceration, projectile injury",
      controls: [
        "Inspect guards and blades before use",
        "Keep hands clear of cutting line",
        "Use dust extraction where available",
      ],
      ppe: ["Safety glasses", "Hearing protection", "Dust mask"],
    },
    {
      id: "carp-fall",
      hazard: "Falls from scaffolding or edges",
      risk: "Serious injury or fatality",
      controls: [
        "Install edge protection before work",
        "Inspect scaffold tags daily",
        "Do not work in high winds",
      ],
      ppe: ["Hard hat", "Harness when required"],
    },
  ],
  general: [
    {
      id: "gen-uv",
      hazard: "UV exposure outdoors",
      risk: "Sunburn, heat stress",
      controls: [
        "Work in shade where possible",
        "Hydration breaks every hour in heat",
        "Reschedule extreme heat work",
      ],
      ppe: ["Broad-brim hat", "SPF 50+ sunscreen", "Long sleeves"],
    },
    {
      id: "gen-public",
      hazard: "Public and client interface",
      risk: "Struck by vehicles, unauthorised access",
      controls: [
        "Barricade work zone",
        "Brief client on access restrictions",
        "High-vis signage at entry points",
      ],
      ppe: ["High-vis vest", "Hard hat"],
    },
  ],
};

const TASK_KEYWORDS: Record<string, string[]> = {
  "elec-live": ["switchboard", "live", "power", "cable", "circuit"],
  "elec-height": ["height", "ladder", "ewp", "roof", "ceiling"],
  "elec-manual": ["cable", "lift", "carry", "install"],
  "plumb-confined": ["roof", "void", "pit", "crawl"],
  "plumb-hot": ["solder", "cut", "braze", "torch"],
  "plumb-slip": ["drain", "leak", "water", "waste"],
  "carp-power": ["cut", "saw", "nail", "trim"],
  "carp-fall": ["scaffold", "edge", "roof", "height"],
  "gen-uv": ["outdoor", "external", "sun"],
  "gen-public": ["client", "public", "footpath", "driveway"],
};

export function selectHazards(
  trade: Trade,
  jobDescription: string,
  tasks: string[],
): HazardControl[] {
  const text = [jobDescription, ...tasks].join(" ").toLowerCase();
  const tradeHazards = HAZARD_LIBRARY[trade];
  const general = HAZARD_LIBRARY.general;

  const matched = new Map<string, HazardControl>();

  for (const h of [...tradeHazards, ...general]) {
    const keywords = TASK_KEYWORDS[h.id] ?? [];
    if (keywords.some((k) => text.includes(k)) || tradeHazards.includes(h)) {
      matched.set(h.id, h);
    }
  }

  if (matched.size === 0) {
    tradeHazards.forEach((h) => matched.set(h.id, h));
  }

  return [...matched.values()];
}
