import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-teal-950 to-teal-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-teal-300">
          Rank #12 · AI Tools SMB
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">QuoteChaser</h1>
        <p className="mt-4 max-w-2xl text-lg text-teal-100">
          Detect unanswered quotes and draft polite staged follow-ups for approval.
          Stops revenue leaking when 40–60% of quotes never get a second touch.
        </p>
        <Link
          href="/dashboard"
          className="mt-10 inline-block rounded-lg bg-teal-400 px-6 py-3 font-semibold text-teal-950 hover:bg-teal-300"
        >
          Open quote chase desk
        </Link>
        <p className="mt-12 text-sm text-teal-300/80">MVP · 6 demo quotes · A$59/mo target pricing</p>
      </main>
    </div>
  );
}
