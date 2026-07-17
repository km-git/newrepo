import { describe, it, expect, beforeEach } from "vitest";
import { parseUrgency, parseCallbackSlot, FLOW_VERSION } from "./call-flow";
import { isEmergency, escalationMessage } from "./emergency-triage";
import { startSession, processUtterance } from "./voice-state-machine";
import {
  resetStore,
  getBusiness,
  getFlowVersion,
  listCalls,
  saveCall,
  saveSession,
} from "./store";
import { purgeRecording } from "./telephony-adapter";

describe("call-flow", () => {
  it("exports versioned flow config", () => {
    expect(FLOW_VERSION).toBe("1.0.0");
    expect(getFlowVersion()).toBe("1.0.0");
  });

  it("parses urgency from caller text", () => {
    expect(parseUrgency("It's an emergency, pipe burst")).toBe("emergency");
    expect(parseUrgency("Can wait until tomorrow")).toBe("routine");
    expect(parseUrgency("Need someone tonight")).toBe("soon");
  });

  it("parses callback slots", () => {
    expect(parseCallbackSlot("7 am works")).toBe("Tomorrow 7–9 am");
    expect(parseCallbackSlot("9 to 11 please")).toBe("Tomorrow 9–11 am");
  });
});

describe("emergency-triage", () => {
  const criteria = getBusiness().emergency;

  it("flags emergency keywords", () => {
    expect(isEmergency("routine", "burst pipe flooding kitchen", criteria)).toBe(true);
    expect(isEmergency("routine", "tap washer replacement", criteria)).toBe(false);
  });

  it("builds escalation SMS body", () => {
    const msg = escalationMessage("RapidFlow", "Parramatta", "burst pipe", "flooding");
    expect(msg).toContain("ON-CALL");
    expect(msg).toContain("Parramatta");
  });
});

describe("voice-state-machine", () => {
  beforeEach(() => resetStore());
  const biz = getBusiness();

  it("starts call with greeting", () => {
    const session = startSession("+61400999888", biz);
    expect(session.state).toBe("JOB_TYPE");
    expect(session.transcript[0].role).toBe("agent");
    expect(session.transcript[0].text).toContain("RapidFlow");
  });

  it("books callback for routine job", () => {
    let session = startSession("+61400999888", biz);
    let result = processUtterance(session, "Leaking tap", biz);
    session = result.session;
    result = processUtterance(session, "Blacktown", biz);
    session = result.session;
    result = processUtterance(session, "not urgent, tomorrow is fine", biz);
    session = result.session;
    result = processUtterance(session, "7 am", biz);
    session = result.session;
    result = processUtterance(session, "thanks", biz);

    expect(session.outcome).toBe("callback_booked");
    expect(session.callbackSlot).toContain("7");
    expect(result.callRecord).toBeDefined();
  });

  it("escalates genuine emergencies", () => {
    let session = startSession("+61400999888", biz);
    let result = processUtterance(session, "Burst pipe", biz);
    session = result.session;
    result = processUtterance(session, "Parramatta", biz);
    session = result.session;
    result = processUtterance(session, "emergency flooding everywhere", biz);
    session = result.session;
    result = processUtterance(session, "water everywhere in kitchen", biz);

    expect(result.escalated).toBe(true);
    expect(session.outcome).toBe("emergency_escalated");
    expect(result.escalationSms).toContain("ON-CALL");
  });
});

describe("store & telephony", () => {
  beforeEach(() => resetStore());

  it("lists saved calls", () => {
    saveCall({
      id: "c1",
      sessionId: "s1",
      phone: "+61400",
      summary: "test",
      outcome: "callback_booked",
      escalated: false,
      createdAt: new Date().toISOString(),
    });
    expect(listCalls().length).toBe(1);
  });

  it("purges recordings in mock mode", () => {
    const { purgedAt } = purgeRecording("call-123");
    expect(purgedAt).toBeTruthy();
  });

  it("persists sessions", () => {
    const session = startSession("+61400", getBusiness());
    saveSession(session);
    expect(session.id).toBeTruthy();
  });
});
