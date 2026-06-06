import { useEffect, useState } from "react";
import { GitCompareArrows, X } from "lucide-react";
import type { ManuscriptPatch, PatchMergePreview } from "@/lib/types";

type PatchMergePanelProps = {
  open: boolean;
  patches: ManuscriptPatch[];
  merge?: PatchMergePreview;
  loading?: boolean;
  actionLoading?: boolean;
  onGenerate: (patchIds: string[]) => Promise<void>;
  onConfirm?: (mergeId: string, decision: "confirmed" | "rejected") => Promise<void>;
  onClose: () => void;
};

export function PatchMergePanel({
  open,
  patches,
  merge,
  loading = false,
  actionLoading = false,
  onGenerate,
  onConfirm,
  onClose
}: PatchMergePanelProps) {
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
              <GitCompareArrows size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">合并 Patch 预览</h2>
                <div className="text-xs font-semibold text-slate-500">不修改 draft.md，不生成 version</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 Patch Merge">
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
              onClick={() => onGenerate(selected)}
            >
              <GitCompareArrows size={16} />
              <span>生成合并预览</span>
            </button>
          </aside>

          <div className="min-w-0 space-y-4">
            {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
            {merge ? (
              <>
                <article
                  className={`rounded-[8px] border p-4 ${
                    merge.can_apply ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"
                  }`}
                >
                  <div className="mb-3 font-mono text-sm font-black text-slate-950">
                    {merge.merge_id}
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                    <div>
                      <dt className="text-slate-400">can_apply</dt>
                      <dd className="mt-1 text-slate-950">{String(merge.can_apply)}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">safe_items</dt>
                      <dd className="mt-1 text-slate-950">{merge.summary.safe_items}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">blocked_items</dt>
                      <dd className="mt-1 text-slate-950">{merge.summary.blocked_items}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">conflicts</dt>
                      <dd className="mt-1 text-slate-950">{merge.summary.conflicts}</dd>
                    </div>
                  </dl>
                  <div className="mt-3 text-xs font-semibold text-slate-600">
                    conflict report: <span className="font-mono">{merge.conflict_report_file}</span>
                  </div>
                  <div className="mt-4 flex flex-wrap justify-end gap-2">
                    <button
                      className="secondary-button"
                      disabled={actionLoading || merge.status !== "preview"}
                      onClick={() => onConfirm?.(merge.merge_id, "rejected")}
                    >
                      <X size={16} />
                      <span>Reject</span>
                    </button>
                    <button
                      className="primary-button"
                      disabled={
                        actionLoading ||
                        merge.status !== "preview" ||
                        !merge.can_apply ||
                        !onConfirm
                      }
                      onClick={() => onConfirm?.(merge.merge_id, "confirmed")}
                    >
                      <GitCompareArrows size={16} />
                      <span>Confirm Version</span>
                    </button>
                  </div>
                  {merge.generated_version_id ? (
                    <div className="mt-3 rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-600">
                      generated_version:{" "}
                      <span className="font-mono text-slate-950">{merge.generated_version_id}</span>
                      {merge.generated_diff_id ? (
                        <>
                          {" "}
                          / diff:{" "}
                          <span className="font-mono text-slate-950">{merge.generated_diff_id}</span>
                        </>
                      ) : null}
                    </div>
                  ) : null}
                </article>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Merge JSON</div>
                  <pre className="max-h-[520px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                    {JSON.stringify(merge, null, 2)}
                  </pre>
                </article>
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                选择 patch 后生成合并预览。
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
