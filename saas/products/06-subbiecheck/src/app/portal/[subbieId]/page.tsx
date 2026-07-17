import { SubbiePortal } from "@/components/SubbiePortal";

export default async function PortalPage({
  params,
}: {
  params: Promise<{ subbieId: string }>;
}) {
  const { subbieId } = await params;
  return (
    <div className="min-h-screen bg-slate-100">
      <main className="mx-auto max-w-2xl px-6 py-12">
        <SubbiePortal subbieId={subbieId} />
      </main>
    </div>
  );
}
