import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-950 to-indigo-900 text-white">
      <main className="mx-auto max-w-4xl px-6 py-20">
        <p className="text-sm font-medium uppercase tracking-widest text-indigo-300">
          Rank #4 · AI Workflow
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          Inbox2Job
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-indigo-100">
          Parse enquiry emails into structured job cards — name, address, job type,
          urgency — then push to ServiceM8 or Tradify with one-tap confirm.
        </p>
        <Link
          href="/dashboard"
          className="mt-10 inline-block rounded-lg bg-indigo-400 px-6 py-3 font-semibold text-indigo-950 hover:bg-indigo-300"
        >
          Open job inbox
        </Link>
        <p className="mt-12 text-sm text-indigo-300/80">
          MVP · Mock platform push · A$39–79/mo target pricing
        </p>
      </main>
    </div>
  );
}
