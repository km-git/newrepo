"use client";

import { useCallback, useEffect, useState } from "react";
import type { Review, ReplyDraft, ToneProfile } from "@/lib/types";

const sentimentStyle: Record<string, string> = {
  positive: "bg-green-100 text-green-800",
  neutral: "bg-slate-100 text-slate-700",
  negative: "bg-red-100 text-red-800",
};

export function ReviewDashboard() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [drafts, setDrafts] = useState<ReplyDraft[]>([]);
  const [profile, setProfile] = useState<ToneProfile | null>(null);
  const [selected, setSelected] = useState<Review | null>(null);
  const [draft, setDraft] = useState<ReplyDraft | null>(null);
  const [editBody, setEditBody] = useState("");
  const [postMsg, setPostMsg] = useState("");

  const refresh = useCallback(async () => {
    const res = await fetch("/api/reviews");
    const data = await res.json();
    setReviews(data.reviews);
    setDrafts(data.drafts);
    setProfile(data.profile);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function draftReply(reviewId: string) {
    const res = await fetch("/api/replies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "draft", reviewId }),
    });
    const data = await res.json();
    setDraft(data.draft);
    setEditBody(data.draft.body);
    const review = reviews.find((r) => r.id === reviewId);
    if (review) setSelected(review);
  }

  async function approve() {
    if (!draft) return;
    await fetch("/api/replies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "update", draftId: draft.id, replyBody: editBody }),
    });
    const res = await fetch("/api/replies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "approve", draftId: draft.id }),
    });
    const data = await res.json();
    setPostMsg(data.result?.message ?? "Posted");
    setDraft(null);
    setSelected(null);
    await refresh();
  }

  async function reject() {
    if (!draft) return;
    await fetch("/api/replies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "reject", draftId: draft.id }),
    });
    setDraft(null);
    await refresh();
  }

  const repliedIds = new Set(drafts.filter((d) => d.status === "posted").map((d) => d.reviewId));

  return (
    <div className="space-y-8">
      {profile && (
        <p className="text-sm text-slate-500">
          Tone: <span className="font-medium capitalize">{profile.style}</span> · {profile.businessName}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Inbox ({reviews.length})</h2>
          <div className="mt-4 space-y-3">
            {reviews.map((r) => {
              const existingDraft = drafts.find((d) => d.reviewId === r.id);
              return (
                <div
                  key={r.id}
                  className={`rounded-lg border p-4 ${selected?.id === r.id ? "border-rose-400 bg-rose-50/30" : ""}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">{r.author}</p>
                      <p className="text-xs text-slate-500">
                        {"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)} · {r.platform}
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${sentimentStyle[r.sentiment]}`}>
                      {r.sentiment}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-700">{r.text}</p>
                  {repliedIds.has(r.id) ? (
                    <span className="mt-2 inline-block text-xs text-green-700">Replied</span>
                  ) : existingDraft ? (
                    <button type="button" onClick={() => { setSelected(r); setDraft(existingDraft); setEditBody(existingDraft.body); }} className="mt-2 text-sm text-rose-600 hover:underline">
                      View draft
                    </button>
                  ) : (
                    <button type="button" onClick={() => draftReply(r.id)} className="mt-2 text-sm font-medium text-rose-600 hover:underline">
                      Draft reply
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Reply editor</h2>
          {!draft ? (
            <p className="mt-4 text-sm text-slate-500">Select a review and draft a reply.</p>
          ) : (
            <div className="mt-4 space-y-4">
              {draft.escalate && (
                <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                  Negative review — owner review recommended before posting.
                </p>
              )}
              <textarea
                rows={5}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
              />
              <div className="flex gap-2">
                <button type="button" onClick={approve} className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-500">
                  Approve &amp; post
                </button>
                <button type="button" onClick={reject} className="rounded-lg border px-4 py-2 text-sm text-slate-600">
                  Reject
                </button>
              </div>
              {postMsg && <p className="text-sm text-green-700">{postMsg}</p>}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
