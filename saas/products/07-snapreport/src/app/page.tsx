import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-950 to-orange-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-orange-300">
          Rank #7 · AI Workflow
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">SnapReport</h1>
        <p className="mt-4 max-w-2xl text-lg text-orange-100">
          Site photos + voice notes → structured, branded completion reports.
          Per-trade templates for electrical, pest, solar, and maintenance. EXIF
          stripped by default.
        </p>
        <div className="mt-10 flex flex-wrap gap-4">
          <Link href="/capture" className="rounded-lg bg-orange-400 px-6 py-3 font-semibold text-orange-950 hover:bg-orange-300">
            New site capture
          </Link>
          <Link href="/dashboard" className="rounded-lg border border-orange-500 px-6 py-3 font-semibold text-orange-200 hover:bg-orange-900">
            View reports
          </Link>
        </div>
        <p className="mt-12 text-sm text-orange-300/80">MVP · Text export · A$49–99/mo target pricing</p>
      </main>
    </div>
  );
}
