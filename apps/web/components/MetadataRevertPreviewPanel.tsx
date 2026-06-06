import { RotateCcw, X } from "lucide-react";
import type { LiteratureMetadataDiffReport, MetadataRevertPreview } from "@/lib/types";

type MetadataRevertPreviewPanelProps = {
  open: boolean;
  diffReport: LiteratureMetadataDiffReport;
  preview?: MetadataRevertPreview;
  loading?: boolean;
  actionLoading?: boolean;
  onPreview: (literatureId: string, field: string, sourceHistoryId: string) => Promise<void>;
  onClose: () => void;
};

export function MetadataRevertPreviewPanel({
  open,
  diffReport,
  preview,
  loading = false,
  actionLoading = false,
  onPreview,
  onClose
}: MetadataRevertPreviewPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <RotateCcw size={20} className="text-[#e59f2f]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Metadata Revert Preview</h2>
                <div className="text-xs font-semibold text-slate-500">{diffReport.records.length} records</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close metadata revert preview">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {preview ? (
            <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
              <div className="font-mono text-sm font-black text-amber-950">{preview.preview_id}</div>
              <dl className="mt-3 grid gap-3 text-xs font-semibold text-amber-900 md:grid-cols-3">
                <div>
                  <dt>field</dt>
                  <dd className="mt-1 font-mono">{preview.field}</dd>
                </div>
                <div>
                  <dt>would_change</dt>
                  <dd className="mt-1 font-mono">{String(preview.would_change)}</dd>
                </div>
                <div>
                  <dt>literature_index_modified</dt>
                  <dd className="mt-1 font-mono">{String(preview.literature_index_modified)}</dd>
                </div>
              </dl>
              <pre className="mt-3 overflow-x-auto rounded-[8px] bg-white/70 p-3 text-xs font-semibold text-amber-950">
                {JSON.stringify({ current_value: preview.current_value, revert_to: preview.revert_to }, null, 2)}
              </pre>
            </article>
          ) : null}

          {diffReport.records.flatMap((record) =>
            record.changes.map((change) => (
              <article key={`${record.literature_id}:${change.field}:${change.source_history_id}`} className="rounded-[8px] border border-slate-200 p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-black text-slate-950">{record.literature_id}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                    {change.field}
                  </span>
                  <span className="font-mono text-xs font-semibold text-slate-500">
                    {change.source_history_id ?? "-"}
                  </span>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <pre className="overflow-x-auto rounded-[8px] bg-rose-50 p-3 text-xs font-semibold text-rose-900">
                    {JSON.stringify(change.old_value, null, 2)}
                  </pre>
                  <pre className="overflow-x-auto rounded-[8px] bg-emerald-50 p-3 text-xs font-semibold text-emerald-900">
                    {JSON.stringify(change.new_value, null, 2)}
                  </pre>
                </div>
                {change.source_history_id ? (
                  <button
                    className="secondary-button mt-3"
                    disabled={actionLoading}
                    onClick={() => onPreview(record.literature_id, change.field, change.source_history_id ?? "")}
                  >
                    <RotateCcw size={16} />
                    <span>Preview Revert</span>
                  </button>
                ) : null}
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
