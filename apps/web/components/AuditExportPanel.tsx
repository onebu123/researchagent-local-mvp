import { Download, ScrollText, X } from "lucide-react";
import type { AuditExport, AuditFileManifest, AuditExportReport, AuditExportSummary } from "@/lib/types";

type AuditExportPanelProps = {
  open: boolean;
  exports: AuditExportSummary[];
  selectedExport?: AuditExport;
  report?: AuditExportReport;
  manifest?: AuditFileManifest;
  loading?: boolean;
  actionLoading?: boolean;
  onCreate: () => Promise<void>;
  onSelectExport: (exportId: string) => Promise<void>;
  onClose: () => void;
};

export function AuditExportPanel({
  open,
  exports,
  selectedExport,
  report,
  manifest,
  loading = false,
  actionLoading = false,
  onCreate,
  onSelectExport,
  onClose
}: AuditExportPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ScrollText size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">导出 Audit Report</h2>
                <div className="text-xs font-semibold text-slate-500">{exports.length} exports</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="primary-button" disabled={actionLoading} onClick={onCreate}>
                <Download size={16} />
                <span>生成导出</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="关闭 Audit Export">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-2">
            {exports.map((item) => (
              <button
                key={item.export_id}
                className={`w-full rounded-[8px] border px-3 py-3 text-left text-sm transition ${
                  selectedExport?.export_id === item.export_id
                    ? "border-[#5b6ee1] bg-indigo-50"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
                onClick={() => onSelectExport(item.export_id)}
              >
                <div className="font-mono font-black text-slate-950">{item.export_id}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">
                  {item.entry_count} entries / valid={String(item.hash_chain_valid)}
                </div>
              </button>
            ))}
          </aside>

          <div className="min-w-0 space-y-4">
            {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
            {selectedExport ? (
              <>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-3 font-mono text-sm font-black text-slate-950">
                    {selectedExport.export_id}
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                    <div>
                      <dt className="text-slate-400">entries</dt>
                      <dd className="mt-1 text-slate-950">{selectedExport.entry_count}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">valid</dt>
                      <dd className="mt-1 text-slate-950">{String(selectedExport.hash_chain_valid)}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">first_invalid</dt>
                      <dd className="mt-1 text-slate-950">
                        {selectedExport.first_invalid_index ?? "-"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">source</dt>
                      <dd className="mt-1 font-mono text-slate-950">{selectedExport.source_file}</dd>
                    </div>
                  </dl>
                </article>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Integrity Report</div>
                  <pre className="max-h-[360px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                    {report?.content ?? "Report is not loaded."}
                  </pre>
                </article>
                {manifest ? (
                  <article className="rounded-[8px] border border-slate-200 p-4">
                    <div className="mb-2 text-sm font-black text-slate-950">File Manifest</div>
                    <dl className="mb-3 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                      <div>
                        <dt className="text-slate-400">files</dt>
                        <dd className="mt-1 text-slate-950">{manifest.file_count}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">warnings</dt>
                        <dd className="mt-1 text-slate-950">{manifest.warnings.length}</dd>
                      </div>
                      <div className="sm:col-span-2">
                        <dt className="text-slate-400">manifest_file</dt>
                        <dd className="mt-1 font-mono text-slate-950">{manifest.relative_path}</dd>
                      </div>
                    </dl>
                    <pre className="max-h-[280px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                      {JSON.stringify(
                        {
                          category_counts: manifest.category_counts,
                          files: manifest.files.slice(0, 20)
                        },
                        null,
                        2
                      )}
                    </pre>
                  </article>
                ) : null}
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Export JSON</div>
                  <pre className="max-h-[360px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                    {JSON.stringify(selectedExport, null, 2)}
                  </pre>
                </article>
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                生成或选择一个 audit export。
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
