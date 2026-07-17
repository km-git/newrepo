import Link from "next/link";
import { AuditDashboard } from "@/components/AuditDashboard";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <Link href="/" className="text-sm text-violet-600 hover:underline">
              ← AuditReady
            </Link>
            <h1 className="text-xl font-bold text-slate-900">Audit workspace</h1>
          </div>
          <span className="text-xs font-medium text-amber-800">
            Organisation tool — not compliance advice
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <AuditDashboard />
      </main>
    </div>
  );
}
