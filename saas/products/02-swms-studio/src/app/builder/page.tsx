import Link from "next/link";
import { SwmsWizard } from "@/components/SwmsWizard";

export default function BuilderPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-amber-700 hover:underline">
            ← SWMS Studio
          </Link>
          <span className="text-xs font-medium uppercase text-amber-600">
            Draft only — PCBU must review
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <SwmsWizard />
      </main>
    </div>
  );
}
