import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-blue-300">
          Rank #1 · AI Receptionist
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          MissedCall Rescue
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-300">
          When tradies miss a call on the tools, instantly SMS back, qualify the job
          in-chat, and deliver a ready-to-call lead card. No sensitive data stored —
          job details and contact number only.
        </p>

        <div className="mt-10 flex flex-wrap gap-4">
          <Link
            href="/dashboard"
            className="rounded-lg bg-blue-500 px-6 py-3 font-semibold text-white hover:bg-blue-400"
          >
            Open dashboard
          </Link>
          <Link
            href="/onboarding"
            className="rounded-lg border border-slate-500 px-6 py-3 font-semibold text-slate-200 hover:bg-slate-800"
          >
            Setup guide
          </Link>
        </div>

        <section className="mt-16 grid gap-6 sm:grid-cols-3">
          {[
            {
              title: "Instant SMS",
              body: "Missed-call webhook triggers a trade-specific qualification script.",
            },
            {
              title: "Lead cards",
              body: "Job type, suburb, urgency, and notes — ready for callback.",
            },
            {
              title: "Emergency alerts",
              body: "Burst pipe or no power? Owner gets an SMS immediately.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-slate-700 bg-slate-800/50 p-5"
            >
              <h2 className="font-semibold text-white">{f.title}</h2>
              <p className="mt-2 text-sm text-slate-400">{f.body}</p>
            </div>
          ))}
        </section>

        <p className="mt-12 text-sm text-slate-500">
          MVP · Mock mode without Twilio credentials · A$49–99/mo target pricing
        </p>
      </main>
    </div>
  );
}
