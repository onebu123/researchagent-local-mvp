import { BookOpenCheck, RefreshCw, X } from "lucide-react";
import type { ManuscriptReferencesPreview, ManuscriptReferencesStatus } from "@/lib/types";

type VerifiedReferencesPanelProps = {
  open: boolean;
  status: ManuscriptReferencesStatus;
  preview: ManuscriptReferencesPreview;
  loading?: boolean;
  actionLoading?: boolean;
  onRefresh: () => Promise<void>;
  onClose: () => void;
};

export function VerifiedReferencesPanel({
  open,
  status,
  preview,
  loading = false,
  actionLoading = false,
  onRefresh,
  onClose
}: VerifiedReferencesPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BookOpenCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Verified References</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {status.verified_references.length} formal / {status.candidate_references.length} candidate / {status.placeholder_records.length} excluded
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Verified References">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <button className="secondary-button" onClick={onRefresh} disabled={actionLoading}>
            <RefreshCw size={16} />
            <span>{actionLoading ? "Refreshing" : "Refresh References"}</span>
          </button>

          <div className="grid gap-3 md:grid-cols-3">
            <article className="rounded-[8px] border border-emerald-200 p-4">
              <div className="text-sm font-black text-emerald-800">Formal References</div>
              <div className="mt-2 text-2xl font-black text-slate-950">{status.verified_references.length}</div>
            </article>
            <article className="rounded-[8px] border border-amber-200 p-4">
              <div className="text-sm font-black text-amber-800">Candidates</div>
              <div className="mt-2 text-2xl font-black text-slate-950">{status.candidate_references.length}</div>
            </article>
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="text-sm font-black text-slate-700">Placeholders</div>
              <div className="mt-2 text-2xl font-black text-slate-950">{status.placeholder_records.length}</div>
            </article>
          </div>

          {status.warnings.length ? (
            <div className="rounded-[8px] bg-amber-50 p-3 text-xs font-semibold text-amber-800 ring-1 ring-amber-200">
              {status.warnings.join(" ")}
            </div>
          ) : null}

          <pre className="max-h-[280px] overflow-auto rounded-[8px] bg-slate-950 p-4 text-xs font-semibold text-slate-50">
            {preview.content}
          </pre>
          <pre className="max-h-[260px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
            {JSON.stringify(status, null, 2)}
          </pre>
        </div>
      </section>
    </div>
  );
}
