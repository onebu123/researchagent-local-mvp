import { BookOpenCheck, RotateCcw, X } from "lucide-react";
import type { LiteratureMetadataDiffReport, LiteratureMetadataRevertSuggestion } from "@/lib/types";

type LiteratureMetadataDiffPanelProps = {
  open: boolean;
  report: LiteratureMetadataDiffReport;
  suggestion?: LiteratureMetadataRevertSuggestion;
  loading?: boolean;
  actionLoading?: boolean;
  onSuggestRevert: (literatureId: string, field: string, sourceHistoryId: string) => Promise<void>;
  onClose: () => void;
};

export function LiteratureMetadataDiffPanel({
  open,
  report,
  suggestion,
  loading = false,
  actionLoading = false,
  onSuggestRevert,
  onClose
}: LiteratureMetadataDiffPanelProps) {
  if (!open) return null;

  const changeCount = report.records.reduce((total, record) => total + record.changes.length, 0);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BookOpenCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Metadata Field Diff</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {changeCount} field changes
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close metadata diff">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {suggestion ? (
            <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
              <div className="mb-2 text-sm font-black text-amber-900">Latest revert suggestion</div>
              <pre className="overflow-x-auto rounded-[8px] bg-white/70 p-3 text-xs font-semibold text-amber-950">
                {JSON.stringify(suggestion, null, 2)}
              </pre>
            </article>
          ) : null}
          {report.records.map((record) => (
            <article key={record.literature_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">
                  {record.literature_id}
                </span>
                <span className="text-sm font-semibold text-slate-700">{record.title ?? "-"}</span>
              </div>
              <div className="mb-3 flex flex-wrap gap-2 text-xs font-semibold text-slate-600">
                <span className="rounded bg-slate-50 px-2 py-1 ring-1 ring-slate-200">
                  added {record.summary.added}
                </span>
                <span className="rounded bg-slate-50 px-2 py-1 ring-1 ring-slate-200">
                  modified {record.summary.modified}
                </span>
                <span className="rounded bg-slate-50 px-2 py-1 ring-1 ring-slate-200">
                  removed {record.summary.removed}
                </span>
              </div>
              <div className="space-y-3">
                {record.changes.map((change) => (
                  <div
                    key={`${record.literature_id}:${change.source_history_id}:${change.field}`}
                    className="rounded-[8px] border border-slate-200 bg-white p-3"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-black text-slate-950">
                          {change.field}
                        </span>
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                          {change.change_type}
                        </span>
                        <span className="font-mono text-xs font-semibold text-slate-500">
                          {change.source_history_id ?? "-"}
                        </span>
                      </div>
                      <button
                        className="secondary-button"
                        disabled={actionLoading || !change.source_history_id}
                        onClick={() =>
                          change.source_history_id &&
                          onSuggestRevert(record.literature_id, change.field, change.source_history_id)
                        }
                      >
                        <RotateCcw size={16} />
                        <span>Suggest Revert</span>
                      </button>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <pre className="overflow-x-auto rounded-[8px] bg-rose-50 p-3 text-xs font-semibold text-rose-900">
                        {JSON.stringify(change.old_value, null, 2)}
                      </pre>
                      <pre className="overflow-x-auto rounded-[8px] bg-emerald-50 p-3 text-xs font-semibold text-emerald-900">
                        {JSON.stringify(change.new_value, null, 2)}
                      </pre>
                    </div>
                    <div className="mt-2 text-xs font-semibold text-slate-500">
                      {change.revert_suggestion.warning}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

