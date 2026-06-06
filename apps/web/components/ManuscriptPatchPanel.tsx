import { Check, FileText, GitCompareArrows, PenLine, RefreshCw, X, XCircle } from "lucide-react";
import type { ManuscriptPatch, ManuscriptPatchItem, ManuscriptPatchPreview } from "@/lib/types";

type ManuscriptPatchPanelProps = {
  open: boolean;
  patches: ManuscriptPatch[];
  selectedPatch?: ManuscriptPatch;
  preview?: ManuscriptPatchPreview;
  loading?: boolean;
  actionLoading?: boolean;
  onGenerate: () => Promise<void>;
  onSelectPatch: (patchId: string) => Promise<void>;
  onConfirm: (patchId: string, decision: "confirmed" | "rejected") => Promise<void>;
  onEditItem?: (patch: ManuscriptPatch, item: ManuscriptPatchItem) => void;
  onSafetyCheck?: (patchId: string, itemId: string) => Promise<void>;
  onOpenConflicts?: () => void;
  onOpenMerge?: () => void;
  onClose: () => void;
};

export function ManuscriptPatchPanel({
  open,
  patches,
  selectedPatch,
  preview,
  loading = false,
  actionLoading = false,
  onGenerate,
  onSelectPatch,
  onConfirm,
  onEditItem,
  onSafetyCheck,
  onOpenConflicts,
  onOpenMerge,
  onClose
}: ManuscriptPatchPanelProps) {
  if (!open) return null;

  const activePatch = selectedPatch ?? patches[0];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <GitCompareArrows size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Manuscript Patch</h2>
                <div className="text-xs font-semibold text-slate-500">{patches.length} patches</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="secondary-button" disabled={actionLoading} onClick={onOpenConflicts}>
                <GitCompareArrows size={16} />
                <span>Conflict</span>
              </button>
              <button className="secondary-button" disabled={actionLoading} onClick={onOpenMerge}>
                <GitCompareArrows size={16} />
                <span>Merge Preview</span>
              </button>
              <button className="primary-button" disabled={actionLoading} onClick={onGenerate}>
                <FileText size={16} />
                <span>Generate Patch</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="关闭 Manuscript Patch">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="space-y-2">
            {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
            {!loading && patches.length === 0 ? (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                暂无 patch，可先接受 revision_diff 后生成。
              </div>
            ) : null}
            {patches.map((patch) => (
              <button
                key={patch.patch_id}
                className={`w-full rounded-[8px] border px-3 py-3 text-left text-sm transition ${
                  activePatch?.patch_id === patch.patch_id
                    ? "border-[#5b6ee1] bg-indigo-50"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
                onClick={() => onSelectPatch(patch.patch_id)}
              >
                <div className="font-mono font-black text-slate-950">{patch.patch_id}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">
                  {patch.status} / {patch.summary.total_items} items
                </div>
              </button>
            ))}
          </aside>

          <div className="min-w-0 space-y-4">
            {activePatch ? (
              <>
                <article className="rounded-[8px] border border-slate-200 bg-white p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-black text-slate-950">
                      {activePatch.patch_id}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                      {activePatch.status}
                    </span>
                    <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                      human confirmation required
                    </span>
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                    <div>
                      <dt className="text-slate-400">source</dt>
                      <dd className="mt-1 font-mono text-slate-950">{activePatch.source_manuscript}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">safe_to_apply</dt>
                      <dd className="mt-1 text-slate-950">{String(activePatch.summary.safe_to_apply)}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">blocked_items</dt>
                      <dd className="mt-1 text-slate-950">{activePatch.summary.blocked_items}</dd>
                    </div>
                  </dl>
                  {activePatch.status === "proposed" ? (
                    <div className="mt-4 flex flex-wrap justify-end gap-2">
                      <button
                        className="secondary-button"
                        disabled={actionLoading}
                        onClick={() => onConfirm(activePatch.patch_id, "rejected")}
                      >
                        <XCircle size={16} />
                        <span>Reject Patch</span>
                      </button>
                      <button
                        className="primary-button"
                        disabled={actionLoading}
                        onClick={() => onConfirm(activePatch.patch_id, "confirmed")}
                      >
                        <Check size={16} />
                        <span>Confirm Patch</span>
                      </button>
                    </div>
                  ) : null}
                </article>

                {activePatch.items.map((item) => (
                  <article key={item.patch_item_id} className="rounded-[8px] border border-slate-200 p-4">
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-black text-slate-950">
                        {item.patch_item_id}
                      </span>
                      <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                        {item.issue_id}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                        {item.change_type}
                      </span>
                      <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700 ring-1 ring-indigo-200">
                        {item.item_status ?? "safe"}
                      </span>
                      {activePatch.status === "proposed" ? (
                        <div className="ml-auto flex flex-wrap gap-2">
                          <button
                            className="secondary-button"
                            disabled={actionLoading}
                            onClick={() => onEditItem?.(activePatch, item)}
                          >
                            <PenLine size={16} />
                            <span>Edit</span>
                          </button>
                          <button
                            className="secondary-button"
                            disabled={actionLoading}
                            onClick={() => onSafetyCheck?.(activePatch.patch_id, item.patch_item_id)}
                          >
                            <RefreshCw size={16} />
                            <span>Safety</span>
                          </button>
                        </div>
                      ) : null}
                    </div>
                    <div className="grid gap-3 lg:grid-cols-2">
                      <div className="rounded-[8px] border border-rose-100 bg-rose-50 p-3">
                        <div className="mb-2 text-xs font-black uppercase text-rose-500">before</div>
                        <p className="text-sm font-semibold leading-6 text-slate-800">{item.before}</p>
                      </div>
                      <div className="rounded-[8px] border border-emerald-100 bg-emerald-50 p-3">
                        <div className="mb-2 text-xs font-black uppercase text-emerald-600">after</div>
                        <p className="text-sm font-semibold leading-6 text-slate-800">{item.after}</p>
                      </div>
                    </div>
                    <dl className="mt-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                      <div>
                        <dt className="text-slate-400">decision_id</dt>
                        <dd className="mt-1 font-mono text-slate-950">{item.decision_id}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">claim_id</dt>
                        <dd className="mt-1 font-mono text-slate-950">
                          {item.related_claim_id ?? "-"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">evidence_status</dt>
                        <dd className="mt-1 text-slate-950">{item.evidence_status ?? "-"}</dd>
                      </div>
                    </dl>
                    {item.warnings.length ? (
                      <ul className="mt-4 space-y-1 text-xs font-semibold leading-5 text-amber-700">
                        {item.warnings.map((warning) => (
                          <li key={warning}>- {warning}</li>
                        ))}
                      </ul>
                    ) : null}
                    {item.latest_safety_result ? (
                      <pre className="mt-4 overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                        {JSON.stringify(item.latest_safety_result, null, 2)}
                      </pre>
                    ) : null}
                  </article>
                ))}

                {activePatch.blocked_items?.length ? (
                  <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
                    <div className="text-sm font-black text-amber-800">Blocked Items</div>
                    <ul className="mt-2 space-y-1 text-xs font-semibold text-amber-800">
                      {activePatch.blocked_items.map((item) => (
                        <li key={item.patch_item_id ?? item.issue_id}>
                          {item.patch_item_id ?? "blocked"}: {item.blocked_reasons.join("; ")}
                        </li>
                      ))}
                    </ul>
                  </article>
                ) : null}

                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Preview Markdown</div>
                  <pre className="max-h-[420px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold leading-5 text-slate-800">
                    {preview?.content ?? "Preview is not loaded."}
                  </pre>
                </article>
              </>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}
