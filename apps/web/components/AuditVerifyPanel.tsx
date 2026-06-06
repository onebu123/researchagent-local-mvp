import { Download, ShieldCheck, X } from "lucide-react";
import type { AuditVerifyResult } from "@/lib/types";

type AuditVerifyPanelProps = {
  open: boolean;
  result: AuditVerifyResult;
  loading?: boolean;
  onRefresh: () => Promise<void>;
  onOpenExport?: () => void;
  onClose: () => void;
};

export function AuditVerifyPanel({
  open,
  result,
  loading = false,
  onRefresh,
  onOpenExport,
  onClose
}: AuditVerifyPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-3xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ShieldCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Audit Hash Chain</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {result.checked_entries} entries checked
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="secondary-button" disabled={loading} onClick={onRefresh}>
                <ShieldCheck size={16} />
                <span>Verify</span>
              </button>
              <button className="secondary-button" disabled={loading} onClick={onOpenExport}>
                <Download size={16} />
                <span>Export</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="关闭审计链校验">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          <article
            className={`rounded-[8px] border p-4 ${
              result.valid ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"
            }`}
          >
            <div className="text-sm font-black text-slate-950">
              {result.valid ? "valid" : "invalid"}
            </div>
            <dl className="mt-3 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
              <div>
                <dt className="text-slate-400">checked_entries</dt>
                <dd className="mt-1 text-slate-950">{result.checked_entries}</dd>
              </div>
              <div>
                <dt className="text-slate-400">first_invalid_index</dt>
                <dd className="mt-1 text-slate-950">{result.first_invalid_index ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-400">scope</dt>
                <dd className="mt-1 text-slate-950">local integrity aid</dd>
              </div>
            </dl>
          </article>

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-2 text-sm font-black text-slate-950">Errors</div>
            {result.errors.length ? (
              <ul className="space-y-1 text-xs font-semibold leading-5 text-rose-700">
                {result.errors.map((error) => (
                  <li key={error}>- {error}</li>
                ))}
              </ul>
            ) : (
              <div className="text-sm font-semibold text-slate-500">No hash chain errors.</div>
            )}
          </article>

          <p className="text-xs font-semibold leading-5 text-slate-500">
            Audit hash chain 只提供本地完整性辅助检查，不是生产级不可篡改审计。
          </p>
        </div>
      </section>
    </div>
  );
}

