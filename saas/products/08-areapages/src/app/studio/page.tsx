import Link from "next/link";
import { PageStudio } from "@/components/PageStudio";

export default function StudioPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm text-sky-600 hover:underline">← AreaPages</Link>
          <span className="text-xs text-slate-500">Review before publish</span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <PageStudio />
      </main>
    </div>
  );
}
