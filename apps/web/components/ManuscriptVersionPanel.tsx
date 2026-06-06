import { FileText, GitCompareArrows, X } from "lucide-react";
import type { ManuscriptVersionContent, ManuscriptVersionHistory } from "@/lib/types";

type ManuscriptVersionPanelProps = {
  open: boolean;
  history: ManuscriptVersionHistory;
  selectedVersion?: ManuscriptVersionContent;
  loading?: boolean;
  onSelectVersion: (versionId: string) => Promise<void>;
  onOpenDiff?: (versionId: string) => Promise<void>;
  onOpenLineage?: () => void;
  onClose: () => void;
};

export function ManuscriptVersionPanel({
  open,
  history,
  selectedVersion,
  loading = false,
  onSelectVersion,
  onOpenDiff,
  onOpenLineage,
  onClose
}: ManuscriptVersionPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Manuscript Versions</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {history.versions.length} versions
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 Manuscript Versions">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="space-y-2">
            {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
            {!loading && history.versions.length === 0 ? (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                暂无 manuscript version。确认 patch 后会在这里出现。
              </div>
            ) : null}
            {history.versions.map((version) => (
              <button
                key={version.version_id}
                className={`w-full rounded-[8px] border px-3 py-3 text-left text-sm transition ${
                  selectedVersion?.version.version_id === version.version_id
                    ? "border-[#5b6ee1] bg-indigo-50"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
                onClick={() => onSelectVersion(version.version_id)}
              >
                <div className="font-mono font-black text-slate-950">{version.version_id}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">
                  {version.status} / {version.summary.applied_items} applied
                </div>
              </button>
            ))}
          </aside>

          <div className="min-w-0 space-y-4">
            {selectedVersion ? (
              <>
                <article className="rounded-[8px] border border-slate-200 bg-white p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-black text-slate-950">
                      {selectedVersion.version.version_id}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                      {selectedVersion.version.status}
                    </span>
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                    <div>
                      <dt className="text-slate-400">source_patch_id</dt>
                      <dd className="mt-1 font-mono text-slate-950">
                        {selectedVersion.version.source_patch_id ?? "-"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">source_merge_id</dt>
                      <dd className="mt-1 font-mono text-slate-950">
                        {selectedVersion.version.source_merge_id ?? "-"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">base_file</dt>
                      <dd className="mt-1 font-mono text-slate-950">{selectedVersion.version.base_file}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">file</dt>
                      <dd className="mt-1 font-mono text-slate-950">{selectedVersion.version.file}</dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="text-slate-400">source_patch_ids</dt>
                      <dd className="mt-1 font-mono text-slate-950">
                        {(selectedVersion.version.source_patch_ids ?? []).join(", ") || "-"}
                      </dd>
                    </div>
                  </dl>
                  <div className="mt-4 text-xs font-semibold text-slate-600">
                    applied={selectedVersion.version.summary.applied_items} / skipped=
                    {selectedVersion.version.summary.skipped_items}
                  </div>
                  <div className="mt-4 flex justify-end gap-2">
                    <button
                      className="secondary-button"
                      disabled={loading}
                      onClick={onOpenLineage}
                    >
                      <GitCompareArrows size={16} />
                      <span>Open Lineage</span>
                    </button>
                    <button
                      className="secondary-button"
                      disabled={loading}
                      onClick={() => onOpenDiff?.(selectedVersion.version.version_id)}
                    >
                      <GitCompareArrows size={16} />
                      <span>Open Diff</span>
                    </button>
                  </div>
                </article>

                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Version Content</div>
                  <pre className="max-h-[560px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold leading-5 text-slate-800">
                    {selectedVersion.content}
                  </pre>
                </article>
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                请选择一个 manuscript version。
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
