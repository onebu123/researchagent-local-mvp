import { FileArchive, FileCheck2, TerminalSquare, X } from "lucide-react";
import type { ReadinessReport, TrustSummary } from "@/lib/types";

type ReleaseReadinessPanelProps = {
  open: boolean;
  report: ReadinessReport;
  trustSummary: TrustSummary;
  loading?: boolean;
  onOpenExport: () => void;
  onRunValidation: () => void;
  onClose: () => void;
};

export function ReleaseReadinessPanel({
  open,
  report,
  trustSummary,
  loading = false,
  onOpenExport,
  onRunValidation,
  onClose
}: ReleaseReadinessPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileCheck2 size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Release Readiness</h2>
                <div className="text-xs font-semibold text-slate-500">{report.readiness_level}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="secondary-button" onClick={onRunValidation}>
                <TerminalSquare size={16} />
                <span>Run validation</span>
              </button>
              <button className="primary-button" onClick={onOpenExport}>
                <FileArchive size={16} />
                <span>Project Export</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="Close release readiness">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-4 lg:grid-cols-3">
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="text-xs font-bold uppercase text-slate-400">trust</div>
              <div className="mt-2 text-xl font-black text-slate-950">{trustSummary.overall_status}</div>
              <div className="mt-1 text-xs font-semibold text-slate-500">
                {trustSummary.blocking_issues.length} blocking items
              </div>
            </article>
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="text-xs font-bold uppercase text-slate-400">local checks</div>
              <div className="mt-2 text-xl font-black text-slate-950">
                {Object.values(report.local_mvp_checks).filter(Boolean).length}/
                {Object.values(report.local_mvp_checks).length}
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-500">v1.0 Local MVP checks</div>
            </article>
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="text-xs font-bold uppercase text-slate-400">validation command</div>
              <div className="mt-2 break-all font-mono text-sm font-black text-slate-950">
                python scripts/validate_v1.py
              </div>
            </article>
          </div>

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

          <div className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
              <div className="mb-3 text-sm font-black text-amber-950">Blocking Items</div>
              <ul className="space-y-2 text-sm font-semibold leading-6 text-amber-900">
                {(report.blocking_gaps.length ? report.blocking_gaps : ["No blocking gap returned by readiness report."]).map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            </article>
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 text-sm font-black text-slate-950">v1.1 Suggestions</div>
              <ul className="space-y-2 text-sm font-semibold leading-6 text-slate-700">
                <li>Authentication and role-based access.</li>
                <li>Production database, backup, restore, and migration path.</li>
                <li>Real DOI/reference verification and OCR integration.</li>
                <li>CI release workflow with hosted smoke tests.</li>
              </ul>
            </article>
          </div>

          <article className="rounded-[8px] border border-rose-200 bg-rose-50 p-4">
            <div className="mb-3 text-sm font-black text-rose-950">Production Gaps</div>
            <ul className="space-y-2 text-sm font-semibold leading-6 text-rose-900">
              {report.production_gaps.map((gap) => (
                <li key={gap}>{gap}</li>
              ))}
            </ul>
          </article>
        </div>
      </section>
    </div>
  );
}
