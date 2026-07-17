import Link from "next/link";
import { ComplianceDashboard } from "@/components/ComplianceDashboard";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <Link href="/" className="text-sm text-teal-700 hover:underline">
              ← SubbieCheck
            </Link>
            <h1 className="text-xl font-bold text-slate-900">Compliance board</h1>
          </div>
          <span className="text-xs font-medium text-amber-800">
            Tracks documents — not compliance advice
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <ComplianceDashboard />
      </main>
    </div>
  );
}
