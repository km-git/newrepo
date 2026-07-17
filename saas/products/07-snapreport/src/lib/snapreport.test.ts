import { describe, it, expect, beforeEach } from "vitest";
import { assembleReport } from "./report-assembler";
import { captionPhoto } from "./photo-captioner";
import { parseVoiceNotes } from "./transcript-parser";
import { getTemplate } from "./report-templates";
import { resetStore, createReport, seedDemoReport } from "./store";

describe("photo-captioner", () => {
  it("generates trade-appropriate caption", () => {
    const photo = captionPhoto("Switchboard after install");
    expect(photo.caption).toContain("Switchboard");
    expect(photo.exifStripped).toBe(true);
  });
});

describe("transcript-parser", () => {
  it("assigns voice notes to sections", () => {
    const notes = parseVoiceNotes(
      ["Replaced switchboard and tested RCD — all passed", "Recommend surge protector upgrade"],
      "electrical",
    );
    expect(notes[0].section).toBeTruthy();
    expect(notes.some((n) => n.section === "recommendations")).toBe(true);
  });
});

describe("report-assembler", () => {
  it("builds complete electrical report", () => {
    const report = assembleReport({
      trade: "electrical",
      jobRef: "JOB-001",
      siteAddress: "1 Test St",
      clientName: "Test Client",
      technician: "Tech One",
      photoLabels: ["Meter box", "After photo"],
      voiceTranscripts: ["Installed new circuits and tested compliance"],
    });

    expect(report.sections.length).toBe(getTemplate("electrical").sections.length);
    expect(report.photos.length).toBe(2);
    expect(report.bodyText).toContain("JOB-001");
    expect(report.bodyText).toContain("EXIF stripped");
    expect(report.status).toBe("draft");
  });

  it("includes solar template sections", () => {
    const report = assembleReport({
      trade: "solar",
      jobRef: "SOL-99",
      siteAddress: "Site",
      clientName: "Client",
      technician: "Tech",
      photoLabels: ["Panel array", "Inverter"],
      voiceTranscripts: ["Commissioned 6.6kW system with monitoring connected"],
    });
    expect(report.sections.some((s) => s.title.includes("Commissioning"))).toBe(true);
  });
});

describe("store", () => {
  beforeEach(() => resetStore());

  it("seeds and lists demo report", () => {
    const report = seedDemoReport();
    expect(report.jobRef).toBe("JOB-2847");
    expect(createReport).toBeDefined();
  });
});
