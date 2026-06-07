import { ShieldCheck, X } from "lucide-react";
import type { CitationSupportReport } from "@/lib/types";

type CitationSupportPanelProps = {
  open: boolean;
  report: CitationSupportReport;
  loading?: boolean;
  onClose: () => void;
};

const tone: Record<string, string> = {
  supported: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  partial: "bg-cyan-50 text-cyan-700 ring-cyan-200",
  unsupported: "bg-rose-50 text-rose-700 ring-rose-200",
  needs_human_review: "bg-amber-50 text-amber-700 ring-amber-200"
};

export function CitationSupportPanel({
  open,
  report,
  loading = false,
  onClose
}: CitationSupportPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ShieldCheck size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Citation Support</h2>
                <div className="text-xs font-semibold text-slate-500">{report.records.length} claims</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Citation Support">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
            v1.2 Citation Grounding adds passage-level grounding strength; Citation Support remains a local overlap check.
          </div>
          {report.records.map((record) => (
            <article key={record.claim_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{record.claim_id}</span>
                <span className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${tone[record.status] ?? tone.partial}`}>
                  {record.status}
                </span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                  overlap={record.overlap_terms}
                </span>
              </div>
              <p className="text-sm font-semibold leading-6 text-slate-600">{record.claim}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {record.matched_chunk_ids.map((chunkId) => (
                  <span key={chunkId} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">
                    {chunkId}
                  </span>
                ))}
              </div>
            </article>
          ))}
          <pre className="max-h-[220px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
            {JSON.stringify({ summary: report.summary, limitations: report.limitations }, null, 2)}
          </pre>
        </div>
      </section>
    </div>
  );
}
