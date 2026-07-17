import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-950 to-emerald-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-emerald-300">
          Rank #3 · AI Workflow
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          InvoiceChase Copilot
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-emerald-100">
          Reads aged receivables (Xero), drafts escalating payment reminders with
          owner approval gates, and classifies debtor replies. Invoice metadata
          only — reminders, not debt collection.
        </p>
        <Link
          href="/dashboard"
          className="mt-10 inline-block rounded-lg bg-emerald-400 px-6 py-3 font-semibold text-emerald-950 hover:bg-emerald-300"
        >
          Open chase dashboard
        </Link>
        <p className="mt-12 text-sm text-emerald-300/80">
          MVP · Mock Xero data · A$59–129/mo target pricing
        </p>
      </main>
    </div>
  );
}
