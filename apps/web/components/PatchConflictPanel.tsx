import { useEffect, useState } from "react";
import { AlertTriangle, GitCompareArrows, X } from "lucide-react";
import type { ManuscriptPatch, PatchConflictReport } from "@/lib/types";

type PatchConflictPanelProps = {
  open: boolean;
  patches: ManuscriptPatch[];
  report?: PatchConflictReport;
  loading?: boolean;
  actionLoading?: boolean;
  onCheck: (patchIds: string[]) => Promise<void>;
  onClose: () => void;
};

export function PatchConflictPanel({
  open,
  patches,
  report,
  loading = false,
  actionLoading = false,
  onCheck,
  onClose
}: PatchConflictPanelProps) {
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    if (open) setSelected(patches.slice(0, 2).map((patch) => patch.patch_id));
  }, [open, patches]);

  if (!open) return null;

  function togglePatch(patchId: string) {
    setSelected((current) =>
      current.includes(patchId)
        ? current.filter((item) => item !== patchId)
        : [...current, patchId]
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <AlertTriangle size={20} className="text-amber-600" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">检查 Patch 冲突</h2>
                <div className="text-xs font-semibold text-slate-500">{patches.length} patches</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 Patch 冲突">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="space-y-2">
            {patches.map((patch) => (
              <label
                key={patch.patch_id}
                className="flex cursor-pointer items-center gap-3 rounded-[8px] border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(patch.patch_id)}
                  onChange={() => togglePatch(patch.patch_id)}
                />
                <span className="font-mono font-black text-slate-950">{patch.patch_id}</span>
                <span className="ml-auto text-xs text-slate-500">{patch.status}</span>
              </label>
            ))}
            <button
              className="primary-button mt-3 w-full justify-center"
              disabled={actionLoading || selected.length === 0}
              onClick={() => onCheck(selected)}
            >
              <GitCompareArrows size={16} />
              <span>运行冲突检查</span>
            </button>
          </aside>

          <div className="min-w-0 space-y-4">
            {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
            {report ? (
              <>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-3 font-mono text-sm font-black text-slate-950">
                    {report.conflict_report_id}
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                    <div>
                      <dt className="text-slate-400">conflicts</dt>
                      <dd className="mt-1 text-slate-950">{report.summary.conflicts}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">major</dt>
                      <dd className="mt-1 text-slate-950">{report.summary.major_conflicts}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">items</dt>
                      <dd className="mt-1 text-slate-950">{report.summary.total_items}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">file</dt>
                      <dd className="mt-1 font-mono text-slate-950">{report.relative_path}</dd>
                    </div>
                  </dl>
                </article>
                {report.conflicts.map((conflict) => (
                  <article key={conflict.conflict_id} className="rounded-[8px] border border-slate-200 p-4">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-black text-slate-950">
                        {conflict.conflict_id}
                      </span>
                      <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                        {conflict.conflict_type}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                        {conflict.severity}
                      </span>
                    </div>
                    <p className="text-sm font-semibold leading-6 text-slate-800">{conflict.message}</p>
                    <pre className="mt-3 overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                      {JSON.stringify(conflict.patch_item_refs, null, 2)}
                    </pre>
                  </article>
                ))}
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                选择 patch 后运行冲突检查。
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

