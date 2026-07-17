import Link from "next/link";
import { WinRateDashboard } from "@/components/WinRateDashboard";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-violet-600 hover:underline">
            ← WinRate Lens
          </Link>
          <h1 className="text-xl font-bold">Quote analytics</h1>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <WinRateDashboard />
      </main>
    </div>
  );
}
