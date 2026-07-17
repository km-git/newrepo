import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-950 to-orange-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-orange-300">
          Rank #13 · Lead Gen
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">DA Lead Miner</h1>
        <p className="mt-4 max-w-2xl text-lg text-orange-100">
          Monitor council development-application approvals in your region. Filter by
          work type, score leads for your trade, and get weekly digests with
          plain-English &quot;why this is a lead for you&quot; summaries.
        </p>
        <Link
          href="/dashboard"
          className="mt-10 inline-block rounded-lg bg-orange-400 px-6 py-3 font-semibold text-orange-950 hover:bg-orange-300"
        >
          Open lead feed
        </Link>
        <p className="mt-12 text-sm text-orange-300/80">MVP · 3 NSW councils · A$79–149/mo per region</p>
      </main>
    </div>
  );
}
