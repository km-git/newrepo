import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-teal-950 to-teal-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-teal-300">
          Rank #6 · Service Platforms
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          SubbieCheck
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-teal-100">
          Subcontractor compliance portal — upload licences, insurances, and white
          cards. AI parses expiry dates for human confirmation. Live compliance
          board with alerts for builders.
        </p>
        <Link
          href="/dashboard"
          className="mt-10 inline-block rounded-lg bg-teal-400 px-6 py-3 font-semibold text-teal-950 hover:bg-teal-300"
        >
          Open compliance board
        </Link>
        <p className="mt-12 text-sm text-teal-300/80">
          MVP · Human-confirmed parsing · A$99–249/mo target pricing
        </p>
      </main>
    </div>
  );
}
