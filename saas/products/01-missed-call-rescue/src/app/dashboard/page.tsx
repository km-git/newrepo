import Link from "next/link";
import { LeadDashboard } from "@/components/LeadDashboard";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div>
            <Link href="/" className="text-sm text-blue-600 hover:underline">
              ← Home
            </Link>
            <h1 className="text-xl font-bold text-slate-900">Lead dashboard</h1>
          </div>
          <Link
            href="/onboarding"
            className="text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            Setup
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <LeadDashboard />
      </main>
    </div>
  );
}
