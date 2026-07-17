import Link from "next/link";
import { ChaseDashboard } from "@/components/ChaseDashboard";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-teal-600 hover:underline">
            ← QuoteChaser
          </Link>
          <h1 className="text-xl font-bold">Quote chase desk</h1>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <ChaseDashboard />
      </main>
    </div>
  );
}
