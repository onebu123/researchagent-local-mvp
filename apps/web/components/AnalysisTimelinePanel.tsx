import { History, X } from "lucide-react";
import type { AnalysisTimeline } from "@/lib/types";

type AnalysisTimelinePanelProps = {
  open: boolean;
  timeline: AnalysisTimeline;
  loading?: boolean;
  onClose: () => void;
};

export function AnalysisTimelinePanel({
  open,
  timeline,
  loading = false,
  onClose
}: AnalysisTimelinePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <History size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Analysis Timeline</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {timeline.summary.runs} runs / {timeline.summary.comparisons} comparisons
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close analysis timeline">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {timeline.change_summary || timeline.failed_run_diagnostics?.length ? (
            <article className="rounded-[8px] border border-slate-200 bg-slate-50/70 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="text-sm font-black text-slate-950">Enhanced change diagnostics</span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  failed runs: {timeline.summary.failed_runs ?? timeline.failed_run_diagnostics?.length ?? 0}
                </span>
              </div>
              {timeline.change_summary ? (
                <dl className="grid gap-3 text-xs font-semibold text-slate-600 md:grid-cols-4">
                  <div>
                    <dt className="text-slate-400">comparisons_with_changes</dt>
                    <dd className="mt-1 text-slate-950">{timeline.change_summary.comparisons_with_changes}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">parameter_changes_total</dt>
                    <dd className="mt-1 text-slate-950">{timeline.change_summary.parameter_changes_total}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">output_hash_changes_total</dt>
                    <dd className="mt-1 text-slate-950">{timeline.change_summary.output_hash_changes_total}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">warning_changes_total</dt>
                    <dd className="mt-1 text-slate-950">{timeline.change_summary.warning_changes_total}</dd>
                  </div>
                </dl>
              ) : null}
              {timeline.failed_run_diagnostics?.length ? (
                <div className="mt-4 grid gap-3">
                  {timeline.failed_run_diagnostics.map((run) => (
                    <div key={run.run_id} className="rounded-[8px] bg-white p-3 ring-1 ring-slate-200">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-black text-rose-700">{run.run_id}</span>
                        <span className="text-xs font-semibold text-slate-500">
                          {run.step ?? "unknown_step"} / {run.retry_hint ?? "no_retry_hint"}
                        </span>
                      </div>
                      <div className="mt-2 text-xs font-semibold text-slate-600">
                        error: {run.error_message ?? run.error_type ?? "-"}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          ) : null}
          {timeline.timeline.map((entry) => (
            <article key={entry.timeline_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">
                  {entry.timeline_id}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {entry.run_id ?? "unlinked"}
                </span>
              </div>
              <div className="text-xs font-semibold text-slate-600">
                provenance: <span className="font-mono text-slate-950">{entry.analysis_provenance}</span>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {(entry.comparisons ?? []).map((comparison) => (
                  <div key={comparison.comparison_id} className="rounded-[8px] bg-slate-50 p-3">
                    <div className="font-mono text-xs font-black text-slate-950">
                      {comparison.comparison_id}
                    </div>
                    <div className="mt-1 text-xs font-semibold text-slate-600">
                      parameters {comparison.summary.parameters_changed} / output hashes{" "}
                      {comparison.summary.output_hash_changes}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
          {timeline.unlinked_comparisons.length ? (
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-2 text-sm font-black text-slate-950">Unlinked comparisons</div>
              <div className="grid gap-2">
                {timeline.unlinked_comparisons.map((comparison) => (
                  <div key={comparison.comparison_id} className="font-mono text-xs font-semibold text-slate-600">
                    {comparison.comparison_id}
                  </div>
                ))}
              </div>
            </article>
          ) : null}
        </div>
      </section>
    </div>
  );
}
