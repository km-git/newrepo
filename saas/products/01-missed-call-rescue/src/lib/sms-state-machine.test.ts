import { describe, it, expect, beforeEach } from "vitest";
import {
  handleInboundSms,
  handleMissedCall,
  isOptOut,
  detectUrgency,
} from "./sms-state-machine";
import { resetStore } from "./store";

describe("sms-state-machine", () => {
  beforeEach(() => {
    resetStore();
  });

  it("starts missed call with trade greeting", () => {
    const { message, session } = handleMissedCall(
      "+61400111222",
      "plumber",
      "Ace Plumbing",
    );
    expect(message).toContain("Ace Plumbing");
    expect(message).toContain("plumbing");
    expect(session.state).toBe("AWAITING_JOB_TYPE");
  });

  it("completes full qualification flow", () => {
    const phone = "+61400111222";
    handleMissedCall(phone, "plumber", "Ace Plumbing");

    handleInboundSms(phone, "Blocked drain", "plumber", "Ace");
    handleInboundSms(phone, "Blacktown", "plumber", "Ace");
    const r3 = handleInboundSms(phone, "soon", "plumber", "Ace");
    const r4 = handleInboundSms(phone, "Easy access", "plumber", "Ace");

    expect(r4.lead).toBeDefined();
    expect(r4.lead!.jobType).toBe("Blocked drain");
    expect(r4.lead!.suburb).toBe("Blacktown");
    expect(r4.lead!.urgency).toBe("soon");
    expect(r4.lead!.status).toBe("ready");
    expect(r4.session.state).toBe("COMPLETE");
    expect(r3.reply).toContain("extra details");
  });

  it("flags emergency from job type keywords", () => {
    const phone = "+61400333444";
    handleMissedCall(phone, "plumber", "Ace");
    const r = handleInboundSms(phone, "Burst pipe flooding", "plumber", "Ace");
    expect(r.notifyOwner).toBe(true);
  });

  it("handles STOP opt-out", () => {
    const phone = "+61400555666";
    handleMissedCall(phone, "plumber", "Ace");
    const r = handleInboundSms(phone, "STOP", "plumber", "Ace");
    expect(r.session.optedOut).toBe(true);
    expect(r.session.state).toBe("OPTED_OUT");
    expect(isOptOut("unsubscribe")).toBe(true);
  });

  it("detects urgency levels", () => {
    expect(detectUrgency("gas leak in kitchen", "plumber")).toBe("emergency");
    expect(detectUrgency("quote for next month", "general")).toBe("routine");
    expect(detectUrgency("need someone today", "electrician")).toBe("soon");
  });
});
