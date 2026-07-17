import Link from "next/link";
import { ReportList } from "@/components/ReportList";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-orange-600 hover:underline">← SnapReport</Link>
          <h1 className="text-xl font-bold">Reports</h1>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-6 py-8">
        <ReportList />
      </main>
    </div>
  );
}
