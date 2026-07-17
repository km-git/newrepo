"use client";

import { useCallback, useEffect, useState } from "react";
import type { CallRecord, VoiceSession } from "@/lib/types";

const outcomeStyle: Record<string, string> = {
  callback_booked: "bg-blue-100 text-blue-800",
  emergency_escalated: "bg-red-100 text-red-800",
  in_progress: "bg-amber-100 text-amber-800",
};

export function CallDashboard() {
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [flowVersion, setFlowVersion] = useState("");
  const [mockMode, setMockMode] = useState(true);
  const [session, setSession] = useState<VoiceSession | null>(null);
  const [utterance, setUtterance] = useState("");
  const [transcript, setTranscript] = useState<{ role: string; text: string }[]>([]);
  const [lastReply, setLastReply] = useState("");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/calls");
    const data = await res.json();
    setCalls(data.calls);
    setFlowVersion(data.flowVersion);
    setMockMode(data.mockMode);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function startCall() {
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "start" }),
    });
    const data = await res.json();
    setSession(data.session);
    setTranscript(data.session.transcript);
    setLastReply(data.greeting);
    setUtterance("");
  }

  async function sendUtterance() {
    if (!session || !utterance.trim()) return;
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "utterance",
        sessionId: session.id,
        utterance,
      }),
    });
    const data = await res.json();
    setSession(data.session);
    setTranscript(data.session.transcript);
    setLastReply(data.reply);
    setUtterance("");
    if (data.callRecord) await refresh();
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap gap-3 text-sm text-slate-500">
        <span>Flow v{flowVersion}</span>
        <span>·</span>
        <span>{mockMode ? "Mock telephony" : "Live Twilio"}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Simulated call</h2>
          {!session ? (
            <button
              type="button"
              onClick={startCall}
              className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
            >
              Start after-hours call
            </button>
          ) : (
            <div className="mt-4 space-y-4">
              <div className="max-h-48 overflow-y-auto rounded-lg bg-slate-50 p-3 text-sm">
                {transcript.map((t, i) => (
                  <p key={i} className={t.role === "agent" ? "text-indigo-700" : "text-slate-700"}>
                    <span className="font-medium capitalize">{t.role}:</span> {t.text}
                  </p>
                ))}
              </div>
              {session.state !== "COMPLETE" ? (
                <div className="flex gap-2">
                  <input
                    type="text"
                    className="flex-1 rounded-lg border px-3 py-2 text-sm"
                    placeholder="Caller says…"
                    value={utterance}
                    onChange={(e) => setUtterance(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendUtterance()}
                  />
                  <button
                    type="button"
                    onClick={sendUtterance}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white"
                  >
                    Send
                  </button>
                </div>
              ) : (
                <p className="text-sm text-green-700">Call complete — {session.outcome.replace("_", " ")}</p>
              )}
              {lastReply && session.state !== "COMPLETE" && (
                <p className="text-xs text-slate-500">Agent will say: {lastReply.slice(0, 80)}…</p>
              )}
            </div>
          )}
        </section>

        <section className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Call log ({calls.length})</h2>
          <div className="mt-4 space-y-3">
            {calls.length === 0 ? (
              <p className="text-sm text-slate-500">No completed calls yet.</p>
            ) : (
              calls.map((c) => (
                <div key={c.id} className="rounded-lg border p-4 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{c.phone}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${outcomeStyle[c.outcome] ?? "bg-slate-100"}`}>
                      {c.outcome.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-600">{c.summary}</p>
                  {c.callbackSlot && (
                    <p className="mt-1 text-xs text-blue-700">Callback: {c.callbackSlot}</p>
                  )}
                  {c.recordingPurgedAt && (
                    <p className="mt-1 text-xs text-slate-400">Recording purged</p>
                  )}
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
