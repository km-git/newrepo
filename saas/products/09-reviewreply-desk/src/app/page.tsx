import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-rose-950 to-rose-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-rose-300">
          Rank #9 · AI Tools SMB
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">ReviewReply Desk</h1>
        <p className="mt-4 max-w-2xl text-lg text-rose-100">
          Draft on-brand replies to Google and Facebook reviews with sentiment
          classification. Human approval before every post — mock GBP integration
          in MVP.
        </p>
        <Link
          href="/dashboard"
          className="mt-10 inline-block rounded-lg bg-rose-400 px-6 py-3 font-semibold text-rose-950 hover:bg-rose-300"
        >
          Open review inbox
        </Link>
        <p className="mt-12 text-sm text-rose-300/80">MVP · 4 demo reviews · A$49–99/mo target pricing</p>
      </main>
    </div>
  );
}
