import { BookOpenCheck, Play, X } from "lucide-react";
import type { BibTeXResponse } from "@/lib/types";

type BibTeXPanelProps = {
  open: boolean;
  data: BibTeXResponse;
  loading?: boolean;
  actionLoading?: boolean;
  onGenerate: () => Promise<void>;
  onClose: () => void;
};

export function BibTeXPanel({
  open,
  data,
  loading = false,
  actionLoading = false,
  onGenerate,
  onClose
}: BibTeXPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BookOpenCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">BibTeX</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {data.report.formal_entries} formal / {data.report.candidate_records ?? 0} candidate / {data.report.skipped_records} skipped
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close BibTeX">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <button className="primary-button" onClick={onGenerate} disabled={actionLoading}>
            <Play size={16} />
            <span>{actionLoading ? "Generating" : "Generate BibTeX"}</span>
          </button>
          <dl className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-2 lg:grid-cols-5">
            <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
              <dt>approved_entries</dt>
              <dd className="font-mono text-slate-950">{data.report.approved_entries ?? data.report.formal_entries}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
              <dt>candidate_records</dt>
              <dd className="font-mono text-slate-950">{data.report.candidate_records ?? 0}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
              <dt>rejected_records</dt>
              <dd className="font-mono text-slate-950">{data.report.rejected_records ?? 0}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
              <dt>placeholder_records</dt>
              <dd className="font-mono text-slate-950">{data.report.placeholder_records ?? 0}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
              <dt>formal_entries</dt>
              <dd className="font-mono text-slate-950">{data.report.formal_entries}</dd>
            </div>
          </dl>
          <pre className="max-h-[360px] overflow-auto rounded-[8px] bg-slate-950 p-4 text-xs font-semibold text-slate-50">
            {data.bibtex}
          </pre>
          <pre className="max-h-[260px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
            {JSON.stringify(data.report, null, 2)}
          </pre>
        </div>
      </section>
    </div>
  );
}
