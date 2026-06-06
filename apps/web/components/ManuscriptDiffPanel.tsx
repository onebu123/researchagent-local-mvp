import { FileText, GitCompareArrows, X } from "lucide-react";
import type {
  ManuscriptDiff,
  ManuscriptDiffPreview,
  ManuscriptVersionHistory
} from "@/lib/types";

type ManuscriptDiffPanelProps = {
  open: boolean;
  history: ManuscriptVersionHistory;
  diffs: ManuscriptDiff[];
  selectedDiff?: ManuscriptDiff;
  preview?: ManuscriptDiffPreview;
  loading?: boolean;
  actionLoading?: boolean;
  onGenerate: (versionId: string) => Promise<void>;
  onSelectDiff: (diffId: string) => Promise<void>;
  onOpenRevisionLineDiff?: () => void;
  onClose: () => void;
};

export function ManuscriptDiffPanel({
  open,
  history,
  diffs,
  selectedDiff,
  preview,
  loading = false,
  actionLoading = false,
  onGenerate,
  onSelectDiff,
  onOpenRevisionLineDiff,
  onClose
}: ManuscriptDiffPanelProps) {
  if (!open) return null;

  const firstVersionId = history.versions[0]?.version_id;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <GitCompareArrows size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">查看 Manuscript Diff</h2>
                <div className="text-xs font-semibold text-slate-500">{diffs.length} diffs</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 Manuscript Diff">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-3">
            <button
              className="primary-button w-full justify-center"
              disabled={actionLoading || !firstVersionId}
              onClick={() => firstVersionId && onGenerate(firstVersionId)}
            >
              <FileText size={16} />
              <span>生成最新版本 Diff</span>
            </button>
            <button
              className="secondary-button w-full justify-center"
              disabled={!onOpenRevisionLineDiff}
              onClick={onOpenRevisionLineDiff}
            >
              <GitCompareArrows size={16} />
              <span>Open Line-level Diff</span>
            </button>
            <div className="space-y-2">
              {diffs.map((diff) => (
                <button
                  key={diff.diff_id}
                  className={`w-full rounded-[8px] border px-3 py-3 text-left text-sm transition ${
                    selectedDiff?.diff_id === diff.diff_id
                      ? "border-[#5b6ee1] bg-indigo-50"
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                  onClick={() => onSelectDiff(diff.diff_id)}
                >
                  <div className="font-mono font-black text-slate-950">{diff.diff_id}</div>
                  <div className="mt-1 text-xs font-semibold text-slate-500">
                    {diff.version_id} / {diff.summary.changed_hunks} hunks
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <div className="min-w-0 space-y-4">
            {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
            {selectedDiff ? (
              <>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-3 font-mono text-sm font-black text-slate-950">
                    {selectedDiff.diff_id}
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                    <div>
                      <dt className="text-slate-400">added</dt>
                      <dd className="mt-1 text-slate-950">{selectedDiff.summary.added_lines}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">removed</dt>
                      <dd className="mt-1 text-slate-950">{selectedDiff.summary.removed_lines}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">hunks</dt>
                      <dd className="mt-1 text-slate-950">{selectedDiff.summary.changed_hunks}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">version</dt>
                      <dd className="mt-1 font-mono text-slate-950">{selectedDiff.version_id}</dd>
                    </div>
                  </dl>
                </article>
                {selectedDiff.hunks.map((hunk) => (
                  <article key={hunk.hunk_id} className="rounded-[8px] border border-slate-200 p-4">
                    <div className="mb-3 font-mono text-sm font-black text-slate-950">{hunk.hunk_id}</div>
                    <div className="grid gap-3 lg:grid-cols-2">
                      <div className="rounded-[8px] border border-rose-100 bg-rose-50 p-3">
                        <div className="mb-2 text-xs font-black uppercase text-rose-500">removed</div>
                        {hunk.removed.map((line) => (
                          <p key={line} className="text-sm font-semibold leading-6 text-slate-800">
                            {line}
                          </p>
                        ))}
                      </div>
                      <div className="rounded-[8px] border border-emerald-100 bg-emerald-50 p-3">
                        <div className="mb-2 text-xs font-black uppercase text-emerald-600">added</div>
                        {hunk.added.map((line) => (
                          <p key={line} className="text-sm font-semibold leading-6 text-slate-800">
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>
                    <div className="mt-3 text-xs font-semibold text-slate-600">
                      issues: {hunk.related_issue_ids.join(", ") || "-"} / claims:{" "}
                      {hunk.related_claim_ids.join(", ") || "-"}
                    </div>
                  </article>
                ))}
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Markdown Preview</div>
                  <pre className="max-h-[360px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                    {preview?.content ?? "Preview is not loaded."}
                  </pre>
                </article>
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                选择或生成一个 manuscript diff。
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
