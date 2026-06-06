import { Filter, X } from "lucide-react";
import type {
  AuditFilteredExport,
  AuditFilteredExportReport,
  AuditFilteredExportSummary
} from "@/lib/types";

type AuditFilterExportPanelProps = {
  open: boolean;
  exports: AuditFilteredExportSummary[];
  selectedExport?: AuditFilteredExport;
  report?: AuditFilteredExportReport;
  riskLevel: string;
  loading?: boolean;
  actionLoading?: boolean;
  onRiskLevelChange: (riskLevel: string) => void;
  onCreate: () => Promise<void>;
  onSelectExport: (exportId: string) => Promise<void>;
  onClose: () => void;
};

export function AuditFilterExportPanel({
  open,
  exports,
  selectedExport,
  report,
  riskLevel,
  loading = false,
  actionLoading = false,
  onRiskLevelChange,
  onCreate,
  onSelectExport,
  onClose
}: AuditFilterExportPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <Filter size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Audit Filter Export</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {exports.length} filtered exports
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close audit filter export">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="grid gap-4 p-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-3">
            <label className="block text-xs font-bold uppercase text-slate-400">risk_level</label>
            <select
              className="w-full rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
              value={riskLevel}
              onChange={(event) => onRiskLevelChange(event.target.value)}
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
            <button className="primary-button w-full justify-center" disabled={actionLoading} onClick={onCreate}>
              <Filter size={16} />
              <span>Create Filtered Export</span>
            </button>
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
                  {item.matching_entry_count} entries / {JSON.stringify(item.filters)}
                </div>
              </button>
            ))}
          </aside>

          <div className="min-w-0 space-y-4">
            {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
            {selectedExport ? (
              <>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="font-mono text-sm font-black text-slate-950">
                    {selectedExport.export_id}
                  </div>
                  <div className="mt-2 text-xs font-semibold text-slate-600">
                    filters: {JSON.stringify(selectedExport.filters)} / entries:{" "}
                    {selectedExport.matching_entry_count}
                  </div>
                </article>
                <article className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-2 text-sm font-black text-slate-950">Markdown Report</div>
                  <pre className="max-h-[520px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                    {report?.content ?? "No report selected."}
                  </pre>
                </article>
              </>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                Select or create a filtered audit export.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
