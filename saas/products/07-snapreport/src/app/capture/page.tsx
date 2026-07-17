import Link from "next/link";
import { CaptureWizard } from "@/components/CaptureWizard";

export default function CapturePage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-orange-600 hover:underline">← SnapReport</Link>
          <Link href="/dashboard" className="text-sm text-slate-600 hover:underline">Reports</Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <CaptureWizard />
      </main>
    </div>
  );
}
