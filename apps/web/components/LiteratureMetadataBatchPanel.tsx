import { BookOpenCheck, X } from "lucide-react";
import type { LiteratureMetadataBatchReview } from "@/lib/types";

type LiteratureMetadataBatchPanelProps = {
  open: boolean;
  batch: LiteratureMetadataBatchReview;
  loading?: boolean;
  onClose: () => void;
};

export function LiteratureMetadataBatchPanel({
  open,
  batch,
  loading = false,
  onClose
}: LiteratureMetadataBatchPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BookOpenCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Metadata Batch Review</h2>
                <div className="text-xs font-semibold text-slate-500">{batch.batch_id}</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close metadata batch">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-3 text-sm font-semibold text-slate-600 sm:grid-cols-5">
            {Object.entries(batch.summary).map(([key, value]) => (
              <div key={key} className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs text-slate-400">{key}</div>
                <div className="mt-1 text-lg font-black text-slate-950">{value}</div>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            {batch.records.map((record) => (
              <article key={record.literature_id} className="rounded-[8px] border border-slate-200 p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-black text-slate-950">
                    {record.literature_id}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                    {record.metadata_status}
                  </span>
                  <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                    {record.recommended_action}
                  </span>
                </div>
                <div className="text-sm font-semibold text-slate-800">{record.title ?? "-"}</div>
                <div className="mt-2 text-xs font-semibold text-slate-500">
                  human_verified={String(record.human_verified)}
                </div>
                <ul className="mt-3 space-y-1 text-sm font-semibold text-slate-600">
                  {record.reasons.map((reason) => (
                    <li key={reason}>- {reason}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

