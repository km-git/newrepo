import type { SuburbData } from "./types";

export const SUBURB_CATALOG: SuburbData[] = [
  {
    slug: "parramatta",
    name: "Parramatta",
    state: "NSW",
    postcode: "2150",
    council: "City of Parramatta",
    landmarks: ["Parramatta Square", "Westfield Parramatta", "Parramatta Park", "Rosehill Gardens"],
    nearbySuburbs: ["Harris Park", "Westmead", "Granville", "North Parramatta"],
  },
  {
    slug: "penrith",
    name: "Penrith",
    state: "NSW",
    postcode: "2750",
    council: "Penrith City Council",
    landmarks: ["Penrith Panthers", "Nepean River", "Westfield Penrith", "Penrith Stadium"],
    nearbySuburbs: ["Kingswood", "Jamisontown", "South Penrith", "Emu Plains"],
  },
  {
    slug: "blacktown",
    name: "Blacktown",
    state: "NSW",
    postcode: "2148",
    council: "Blacktown City Council",
    landmarks: ["Blacktown Hospital", "Westpoint Blacktown", "Nurragingy Reserve"],
    nearbySuburbs: ["Seven Hills", "Mount Druitt", "Prospect", "Quakers Hill"],
  },
  {
    slug: "liverpool",
    name: "Liverpool",
    state: "NSW",
    postcode: "2170",
    council: "Liverpool City Council",
    landmarks: ["Westfield Liverpool", "Liverpool Hospital", "Bigge Park"],
    nearbySuburbs: ["Moorebank", "Warwick Farm", "Casula", "Prestons"],
  },
];

export function getSuburb(slug: string): SuburbData | undefined {
  return SUBURB_CATALOG.find((s) => s.slug === slug);
}

export function listSuburbs(): SuburbData[] {
  return SUBURB_CATALOG;
}
