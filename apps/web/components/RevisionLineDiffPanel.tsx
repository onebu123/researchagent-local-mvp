import { GitCompareArrows, X } from "lucide-react";
import type { ManuscriptVersionHistory, RevisionLineDiff } from "@/lib/types";

type RevisionLineDiffPanelProps = {
  open: boolean;
  history: ManuscriptVersionHistory;
  diffs: RevisionLineDiff[];
  selectedDiff?: RevisionLineDiff;
  loading?: boolean;
  actionLoading?: boolean;
  onGenerate: (targetFile: string) => Promise<void>;
  onSelectDiff: (revisionDiffId: string) => Promise<void>;
  onClose: () => void;
};

export function RevisionLineDiffPanel({
  open,
  history,
  diffs,
  selectedDiff,
  loading = false,
  actionLoading = false,
  onGenerate,
  onSelectDiff,
  onClose
}: RevisionLineDiffPanelProps) {
  if (!open) return null;

  const firstTargetFile = history.versions[0]?.file;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <GitCompareArrows size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Revision Line Diff</h2>
                <div className="text-xs font-semibold text-slate-500">{diffs.length} reports</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close revision line diff">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-3">
            <button
              className="primary-button w-full justify-center"
              disabled={actionLoading || !firstTargetFile}
              onClick={() => firstTargetFile && onGenerate(firstTargetFile)}
            >
              <GitCompareArrows size={16} />
              <span>Generate Line Diff</span>
            </button>
            {diffs.map((diff) => (
              <button
                key={diff.revision_diff_id}
                className={`w-full rounded-[8px] border px-3 py-3 text-left text-sm transition ${
                  selectedDiff?.revision_diff_id === diff.revision_diff_id
                    ? "border-[#5b6ee1] bg-indigo-50"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
                onClick={() => onSelectDiff(diff.revision_diff_id)}
              >
                <div className="font-mono font-black text-slate-950">
                  {diff.revision_diff_id}
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-500">
                  {diff.summary.lines_changed} lines / {diff.summary.sentences_changed} sentences
                </div>
              </button>
            ))}
          </aside>

          <div className="min-w-0 space-y-4">
            {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
            {selectedDiff ? (
              <>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-3 font-mono text-sm font-black text-slate-950">
                    {selectedDiff.revision_diff_id}
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                    <div>
                      <dt className="text-slate-400">base_file</dt>
                      <dd className="mt-1 break-all font-mono text-slate-950">
                        {selectedDiff.base_file}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">target_file</dt>
                      <dd className="mt-1 break-all font-mono text-slate-950">
                        {selectedDiff.target_file}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">issues / claims</dt>
                      <dd className="mt-1 text-slate-950">
                        {selectedDiff.summary.issues_linked} / {selectedDiff.summary.claims_linked}
                      </dd>
                    </div>
                  </dl>
                </article>
                {selectedDiff.changes.map((change) => (
                  <article key={change.change_id} className="rounded-[8px] border border-slate-200 p-4">
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-black text-slate-950">
                        {change.change_id}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                        {change.section}
                      </span>
                      <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">
                        {change.safety_status}
                      </span>
                    </div>
                    <dl className="mb-3 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                      <div>
                        <dt className="text-slate-400">paragraph</dt>
                        <dd className="mt-1 text-slate-950">{change.paragraph_index}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">sentence</dt>
                        <dd className="mt-1 text-slate-950">{change.sentence_index}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">line_start</dt>
                        <dd className="mt-1 text-slate-950">{change.line_start}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">line_end</dt>
                        <dd className="mt-1 text-slate-950">{change.line_end}</dd>
                      </div>
                    </dl>
                    <div className="grid gap-3 lg:grid-cols-2">
                      <pre className="overflow-x-auto rounded-[8px] bg-rose-50 p-3 text-xs font-semibold text-rose-900">
                        {change.before || "-"}
                      </pre>
                      <pre className="overflow-x-auto rounded-[8px] bg-emerald-50 p-3 text-xs font-semibold text-emerald-900">
                        {change.after || "-"}
                      </pre>
                    </div>
                    <div className="mt-3 text-xs font-semibold text-slate-600">
                      issues: {change.related_issue_ids.join(", ") || "-"} / claims:{" "}
                      {change.related_claim_ids.join(", ") || "-"}
                    </div>
                  </article>
                ))}
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                Select or generate a revision line diff.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

