import { Activity, X } from "lucide-react";
import type { AnalysisComparison } from "@/lib/types";

type AnalysisComparePanelProps = {
  open: boolean;
  comparisons: AnalysisComparison[];
  selectedComparison?: AnalysisComparison;
  loading?: boolean;
  actionLoading?: boolean;
  onGenerate: () => Promise<void>;
  onSelectComparison: (comparisonId: string) => Promise<void>;
  onClose: () => void;
};

export function AnalysisComparePanel({
  open,
  comparisons,
  selectedComparison,
  loading = false,
  actionLoading = false,
  onGenerate,
  onSelectComparison,
  onClose
}: AnalysisComparePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <Activity size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Analysis Comparison</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {comparisons.length} comparisons
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close analysis compare">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-3">
            <button className="primary-button w-full justify-center" disabled={actionLoading} onClick={onGenerate}>
              <Activity size={16} />
              <span>Generate Compare</span>
            </button>
            {comparisons.map((comparison) => (
              <button
                key={comparison.comparison_id}
                className={`w-full rounded-[8px] border px-3 py-3 text-left text-sm transition ${
                  selectedComparison?.comparison_id === comparison.comparison_id
                    ? "border-[#5b6ee1] bg-indigo-50"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
                onClick={() => onSelectComparison(comparison.comparison_id)}
              >
                <div className="font-mono font-black text-slate-950">
                  {comparison.comparison_id}
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-500">
                  parameters {comparison.summary.parameters_changed} / output hashes{" "}
                  {comparison.summary.output_hash_changes}
                </div>
              </button>
            ))}
          </aside>

          <div className="min-w-0 space-y-4">
            {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
            {selectedComparison ? (
              <>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-3 font-mono text-sm font-black text-slate-950">
                    {selectedComparison.comparison_id}
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                    <div>
                      <dt className="text-slate-400">base_provenance</dt>
                      <dd className="mt-1 break-all font-mono text-slate-950">
                        {selectedComparison.base_provenance}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">target_provenance</dt>
                      <dd className="mt-1 break-all font-mono text-slate-950">
                        {selectedComparison.target_provenance}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">input_hash_changed</dt>
                      <dd className="mt-1 text-slate-950">
                        {String(selectedComparison.summary.input_hash_changed)}
                      </dd>
                    </div>
                  </dl>
                </article>
                {Object.entries(selectedComparison.diffs).map(([key, value]) => (
                  <article key={key} className="rounded-[8px] border border-slate-200 p-4">
                    <div className="mb-2 text-sm font-black text-slate-950">{key}</div>
                    <pre className="max-h-[320px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  </article>
                ))}
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                Select or generate an analysis comparison.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

