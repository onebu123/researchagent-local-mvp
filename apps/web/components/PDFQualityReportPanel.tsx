import { FileText, X } from "lucide-react";
import type { PDFQualityReport } from "@/lib/types";

type PDFQualityReportPanelProps = {
  open: boolean;
  report: PDFQualityReport;
  loading?: boolean;
  onClose: () => void;
};

export function PDFQualityReportPanel({
  open,
  report,
  loading = false,
  onClose
}: PDFQualityReportPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">PDF Quality Report</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {report.summary.pdf_count} PDFs
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close PDF quality report">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-3 text-sm font-semibold text-slate-600 sm:grid-cols-3">
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs text-slate-400">pdf_count</div>
              <div className="mt-1 text-lg font-black text-slate-950">
                {report.summary.pdf_count}
              </div>
            </div>
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs text-slate-400">low_quality_pdf_count</div>
              <div className="mt-1 text-lg font-black text-slate-950">
                {report.summary.low_quality_pdf_count}
              </div>
            </div>
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs text-slate-400">pages_requiring_review</div>
              <div className="mt-1 text-lg font-black text-slate-950">
                {report.summary.pages_requiring_review}
              </div>
            </div>
          </div>

          {report.pdfs.map((pdf) => (
            <article key={pdf.source_file} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">
                  {pdf.source_file}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {pdf.quality_label}
                </span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                  {pdf.recommended_action}
                </span>
              </div>
              <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                <div>
                  <dt className="text-slate-400">quality_score</dt>
                  <dd className="mt-1 text-slate-950">{pdf.quality_score}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">page_count</dt>
                  <dd className="mt-1 text-slate-950">{pdf.page_count}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">low_quality_pages</dt>
                  <dd className="mt-1 font-mono text-slate-950">
                    {pdf.low_quality_pages.join(", ") || "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">suspected_scanned_pages</dt>
                  <dd className="mt-1 font-mono text-slate-950">
                    {pdf.suspected_scanned_pages.join(", ") || "-"}
                  </dd>
                </div>
              </dl>
              <pre className="mt-3 overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                {JSON.stringify(pdf.issue_categories, null, 2)}
              </pre>
              <div className="mt-3 text-xs font-semibold text-slate-500">
                OCR attempted: {String(pdf.ocr_attempted)}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

