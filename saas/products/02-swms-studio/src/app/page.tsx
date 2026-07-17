import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-950 to-amber-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-amber-300">
          Rank #2 · Tradie / NDIS
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          SWMS Studio
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-amber-100">
          Generate job-specific Safe Work Method Statement drafts from guided
          Q&amp;A and a per-trade hazard/control library. Clearly positioned as
          drafts the PCBU must review and sign off.
        </p>
        <Link
          href="/builder"
          className="mt-10 inline-block rounded-lg bg-amber-500 px-6 py-3 font-semibold text-amber-950 hover:bg-amber-400"
        >
          Open SWMS builder
        </Link>
        <p className="mt-12 text-sm text-amber-300/80">
          MVP · Text export · A$29–69/mo target pricing
        </p>
      </main>
    </div>
  );
}
