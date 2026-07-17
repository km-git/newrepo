import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-950 to-sky-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-sky-300">Rank #8 · AI Content+SEO</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">AreaPages</h1>
        <p className="mt-4 max-w-2xl text-lg text-sky-100">
          Generate unique, locally-grounded suburb × service pages with landmarks,
          council context, and your real job references. Human review before
          WordPress publish.
        </p>
        <Link href="/studio" className="mt-10 inline-block rounded-lg bg-sky-400 px-6 py-3 font-semibold text-sky-950 hover:bg-sky-300">
          Open page studio
        </Link>
        <p className="mt-12 text-sm text-sky-300/80">MVP · 4 NSW suburbs · A$79–199/mo target pricing</p>
      </main>
    </div>
  );
}
