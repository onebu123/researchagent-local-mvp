import { FileText, X } from "lucide-react";
import type { SourcePassageEvidenceReport } from "@/lib/types";

type SourcePassageEvidencePanelProps = {
  open: boolean;
  report: SourcePassageEvidenceReport;
  loading?: boolean;
  onClose: () => void;
};

export function SourcePassageEvidencePanel({
  open,
  report,
  loading = false,
  onClose
}: SourcePassageEvidencePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Source Passage Evidence</h2>
                <div className="text-xs font-semibold text-slate-500">{report.records.length} records</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Source Passage Evidence">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {report.records.map((record) => (
            <article key={record.evidence_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{record.evidence_id}</span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                  {record.support_status}
                </span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                  {record.metadata_status}
                </span>
              </div>
              <div className="break-all font-mono text-xs font-semibold text-slate-500">{record.chunk_id}</div>
              <p className="mt-3 text-sm font-semibold leading-6 text-slate-600">{record.excerpt}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
