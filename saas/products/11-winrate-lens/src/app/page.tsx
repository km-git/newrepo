import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-violet-950 to-violet-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-violet-300">
          Rank #11 · Analytics
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">WinRate Lens</h1>
        <p className="mt-4 max-w-2xl text-lg text-violet-100">
          See which job types, suburbs, and price bands you actually win. Pulls quote
          data from ServiceM8 (mock in MVP) and turns metrics into plain-English
          monthly insights.
        </p>
        <Link
          href="/dashboard"
          className="mt-10 inline-block rounded-lg bg-violet-400 px-6 py-3 font-semibold text-violet-950 hover:bg-violet-300"
        >
          Open win-rate dashboard
        </Link>
        <p className="mt-12 text-sm text-violet-300/80">MVP · 10 demo quotes · A$49–99/mo target pricing</p>
      </main>
    </div>
  );
}
