import Link from "next/link";

export default function OnboardingPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-2xl px-6 py-12">
        <Link href="/" className="text-sm text-blue-600 hover:underline">
          ← Home
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-slate-900">Setup wizard</h1>
        <ol className="mt-8 list-decimal space-y-6 pl-5 text-slate-700">
          <li>
            <strong>Twilio account</strong> — buy an AU mobile number and enable SMS +
            voice webhooks.
          </li>
          <li>
            <strong>Webhooks</strong>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              <li>
                Voice (missed call):{" "}
                <code className="rounded bg-slate-200 px-1">
                  /api/webhooks/twilio/missed-call
                </code>
              </li>
              <li>
                SMS inbound:{" "}
                <code className="rounded bg-slate-200 px-1">
                  /api/webhooks/twilio/sms
                </code>
              </li>
            </ul>
          </li>
          <li>
            <strong>Environment</strong> — copy <code>.env.example</code> to{" "}
            <code>.env.local</code> and fill Twilio + optional Supabase/Stripe keys.
          </li>
          <li>
            <strong>Trade script</strong> — set <code>DEFAULT_TRADE=plumber</code>{" "}
            (or electrician, general).
          </li>
          <li>
            <strong>Compliance</strong> — STOP/opt-out is built in. Include business name
            in the first SMS. Review ACMA SMS rules before going live.
          </li>
        </ol>
        <Link
          href="/dashboard"
          className="mt-8 inline-block rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
        >
          Open dashboard
        </Link>
      </div>
    </div>
  );
}
