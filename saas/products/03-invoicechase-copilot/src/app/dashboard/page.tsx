import Link from "next/link";
import { ChaseDashboard } from "@/components/ChaseDashboard";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <Link href="/" className="text-sm text-emerald-700 hover:underline">
              ← InvoiceChase Copilot
            </Link>
            <h1 className="text-xl font-bold text-slate-900">Chase dashboard</h1>
          </div>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
            Reminders only — not debt collection
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <ChaseDashboard />
      </main>
    </div>
  );
}
