import Link from "next/link";
import { ReviewDashboard } from "@/components/ReviewDashboard";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-rose-600 hover:underline">
            ← ReviewReply Desk
          </Link>
          <h1 className="text-xl font-bold">Review inbox</h1>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <ReviewDashboard />
      </main>
    </div>
  );
}
