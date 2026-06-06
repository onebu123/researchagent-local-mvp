import { useEffect, useState } from "react";
import { RefreshCw, Save, X } from "lucide-react";
import type { ManuscriptPatch, ManuscriptPatchItem } from "@/lib/types";

type PatchItemEditorPanelProps = {
  open: boolean;
  patch?: ManuscriptPatch;
  item?: ManuscriptPatchItem;
  loading?: boolean;
  actionLoading?: boolean;
  onSave: (patchId: string, itemId: string, after: string, reason: string) => Promise<void>;
  onSafetyCheck: (patchId: string, itemId: string) => Promise<void>;
  onClose: () => void;
};

export function PatchItemEditorPanel({
  open,
  patch,
  item,
  loading = false,
  actionLoading = false,
  onSave,
  onSafetyCheck,
  onClose
}: PatchItemEditorPanelProps) {
  const [after, setAfter] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    setAfter(item?.after ?? "");
    setReason("");
  }, [item?.patch_item_id, item?.after]);

  if (!open) return null;

  const canEdit = Boolean(patch && item && patch.status === "proposed");

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-lg font-black">编辑 Patch Item</h2>
              <div className="text-xs font-semibold text-slate-500">
                {patch?.patch_id ?? "-"} / {item?.patch_item_id ?? "-"}
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 Patch Item 编辑">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!patch || !item ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              当前没有可编辑的 patch item。
            </div>
          ) : (
            <>
              <article className="rounded-[8px] border border-slate-200 p-4">
                <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                  <div>
                    <dt className="text-slate-400">status</dt>
                    <dd className="mt-1 font-mono text-slate-950">{item.item_status ?? "safe"}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">issue_id</dt>
                    <dd className="mt-1 font-mono text-slate-950">{item.issue_id}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">claim_id</dt>
                    <dd className="mt-1 font-mono text-slate-950">{item.related_claim_id ?? "-"}</dd>
                  </div>
                </dl>
                <div className="mt-4 rounded-[8px] border border-rose-100 bg-rose-50 p-3">
                  <div className="mb-2 text-xs font-black uppercase text-rose-500">before</div>
                  <p className="text-sm font-semibold leading-6 text-slate-800">{item.before}</p>
                </div>
              </article>

              <article className="rounded-[8px] border border-slate-200 p-4">
                <label className="text-xs font-black uppercase text-slate-500" htmlFor="patch-after">
                  after
                </label>
                <textarea
                  id="patch-after"
                  className="mt-2 min-h-[180px] w-full rounded-[8px] border border-slate-200 bg-white p-3 text-sm font-semibold leading-6 text-slate-800 outline-none focus:border-[#5b6ee1]"
                  value={after}
                  disabled={!canEdit || actionLoading}
                  onChange={(event) => setAfter(event.target.value)}
                />
                <label className="mt-4 block text-xs font-black uppercase text-slate-500" htmlFor="patch-reason">
                  reason
                </label>
                <input
                  id="patch-reason"
                  className="mt-2 w-full rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 outline-none focus:border-[#5b6ee1]"
                  value={reason}
                  disabled={!canEdit || actionLoading}
                  onChange={(event) => setReason(event.target.value)}
                />
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    className="secondary-button"
                    disabled={!canEdit || actionLoading}
                    onClick={() => onSafetyCheck(patch.patch_id, item.patch_item_id)}
                  >
                    <RefreshCw size={16} />
                    <span>重新安全检查</span>
                  </button>
                  <button
                    className="primary-button"
                    disabled={!canEdit || actionLoading || !after.trim()}
                    onClick={() => onSave(patch.patch_id, item.patch_item_id, after, reason)}
                  >
                    <Save size={16} />
                    <span>保存 after</span>
                  </button>
                </div>
              </article>

              <article className="rounded-[8px] border border-slate-200 p-4">
                <div className="mb-2 text-sm font-black text-slate-950">Latest Safety Result</div>
                <pre className="overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                  {JSON.stringify(item.latest_safety_result ?? null, null, 2)}
                </pre>
              </article>

              {item.manual_edits?.length ? (
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Manual Edits</div>
                  <div className="space-y-2">
                    {item.manual_edits.map((edit) => (
                      <div key={edit.edit_id} className="rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-700">
                        <div className="font-mono font-black text-slate-950">{edit.edit_id}</div>
                        <div className="mt-1">{edit.reason || "-"}</div>
                        <div className="mt-1 text-slate-500">{edit.created_at}</div>
                      </div>
                    ))}
                  </div>
                </article>
              ) : null}
            </>
          )}
        </div>
      </section>
    </div>
  );
}

