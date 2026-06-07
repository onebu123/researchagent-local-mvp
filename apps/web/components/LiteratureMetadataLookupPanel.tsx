import { Database, Play, X } from "lucide-react";
import type { LiteratureMetadataLookupResponse } from "@/lib/types";

type LiteratureMetadataLookupPanelProps = {
  open: boolean;
  result: LiteratureMetadataLookupResponse;
  provider: string;
  loading?: boolean;
  actionLoading?: boolean;
  onProviderChange: (provider: string) => void;
  onRun: () => Promise<void>;
  onClose: () => void;
};

export function LiteratureMetadataLookupPanel({
  open,
  result,
  provider,
  loading = false,
  actionLoading = false,
  onProviderChange,
  onRun,
  onClose
}: LiteratureMetadataLookupPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <Database size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Metadata Lookup</h2>
                <div className="text-xs font-semibold text-slate-500">{result.results.length} results</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Metadata Lookup">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="flex flex-wrap items-center gap-3">
            <select
              className="rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-bold text-slate-950"
              value={provider}
              onChange={(event) => onProviderChange(event.target.value)}
            >
              <option value="mock_fixture">mock_fixture</option>
              <option value="crossref_optional">crossref_optional</option>
              <option value="semantic_scholar_optional">semantic_scholar_optional</option>
            </select>
            <button className="primary-button" onClick={onRun} disabled={actionLoading}>
              <Play size={16} />
              <span>{actionLoading ? "Running" : "Run Lookup"}</span>
            </button>
            <span className="rounded-full bg-slate-50 px-3 py-2 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
              v1.2 reference verification still requires explicit approval before apply
            </span>
          </div>
          {result.results.map((record) => (
            <article key={record.lookup_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{record.lookup_id}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {record.provider}
                </span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                  {record.status}
                </span>
              </div>
              <div className="text-sm font-bold text-slate-950">{record.query_title}</div>
              <pre className="mt-3 max-h-[220px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                {JSON.stringify(record.candidates, null, 2)}
              </pre>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
