import { FileCheck2, X } from "lucide-react";
import type { ReadinessReport } from "@/lib/types";

type ReadinessReportPanelProps = {
  open: boolean;
  report: ReadinessReport;
  loading?: boolean;
  onClose: () => void;
};

export function ReadinessReportPanel({
  open,
  report,
  loading = false,
  onClose
}: ReadinessReportPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileCheck2 size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">v1.0 Readiness</h2>
                <div className="text-xs font-semibold text-slate-500">{report.readiness_level}</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close readiness report">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Local MVP Checks</div>
            <dl className="grid gap-2 text-xs font-semibold text-slate-600 md:grid-cols-2">
              {Object.entries(report.local_mvp_checks).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between rounded bg-slate-50 px-3 py-2">
                  <dt>{key}</dt>
                  <dd className="font-mono text-slate-950">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </article>
          <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
            <div className="mb-3 text-sm font-black text-amber-950">Production Gaps</div>
            <ul className="space-y-2 text-sm font-semibold leading-6 text-amber-900">
              {report.production_gaps.map((gap) => (
                <li key={gap}>{gap}</li>
              ))}
            </ul>
          </article>
          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Next Steps</div>
            <ul className="space-y-2 text-sm font-semibold leading-6 text-slate-700">
              {report.recommended_next_steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
          </article>
        </div>
      </section>
    </div>
  );
}
