import { FileText, X } from "lucide-react";
import type { PDFPageReviewStatus, PDFPageReviewsResponse, PDFQualityReport } from "@/lib/types";

type PDFPageReviewPanelProps = {
  open: boolean;
  report: PDFQualityReport;
  reviewState: PDFPageReviewsResponse;
  loading?: boolean;
  actionLoading?: boolean;
  onOpenTextPreview?: () => void;
  onReview: (sourceFile: string, pageNumber: number, status: PDFPageReviewStatus) => Promise<void>;
  onClose: () => void;
};

const statuses: PDFPageReviewStatus[] = [
  "accepted_as_readable",
  "needs_ocr",
  "ignore_page",
  "needs_manual_check"
];

function pagesForReview(record: PDFQualityReport["pdfs"][number]): number[] {
  const pages = new Set<number>([
    ...record.low_quality_pages,
    ...record.empty_pages,
    ...record.suspected_scanned_pages
  ]);
  if (pages.size === 0 && record.page_count > 0) pages.add(1);
  return Array.from(pages).sort((a, b) => a - b);
}

export function PDFPageReviewPanel({
  open,
  report,
  reviewState,
  loading = false,
  actionLoading = false,
  onOpenTextPreview,
  onReview,
  onClose
}: PDFPageReviewPanelProps) {
  if (!open) return null;

  const latest = new Map(
    reviewState.summary.pages.map((page) => [`${page.source_file}:${page.page_number}`, page])
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText size={20} className="text-[#e59f2f]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">PDF Page Review</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {reviewState.summary.summary.total_reviews} page reviews
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {onOpenTextPreview ? (
                <button className="secondary-button" onClick={onOpenTextPreview} aria-label="PDF Page Text Preview">
                  <FileText size={15} />
                  <span>Text Preview</span>
                </button>
              ) : null}
              <button className="icon-button" onClick={onClose} aria-label="Close PDF page review">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {report.pdfs.map((pdf) => (
            <article key={pdf.source_file} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="break-all font-mono text-sm font-black text-slate-950">
                  {pdf.source_file}
                </span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                  {pdf.quality_label}
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  low pages: {pdf.low_quality_pages.join(", ") || "-"} / suspected scanned:{" "}
                  {pdf.suspected_scanned_pages.join(", ") || "-"}
                </span>
              </div>
              <div className="grid gap-3">
                {pagesForReview(pdf).map((pageNumber) => {
                  const review = latest.get(`${pdf.source_file}:${pageNumber}`);
                  return (
                    <div key={pageNumber} className="rounded-[8px] bg-slate-50 p-3">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-black text-slate-950">
                          page {pageNumber}
                        </span>
                        <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                          {review?.latest_human_status ?? "unreviewed"}
                        </span>
                        <span className="text-xs font-semibold text-slate-500">
                          signal: {review?.auto_quality_signal ?? "from_quality_report"}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {statuses.map((status) => (
                          <button
                            key={status}
                            className="secondary-button"
                            disabled={actionLoading}
                            onClick={() => onReview(pdf.source_file, pageNumber, status)}
                          >
                            <FileText size={15} />
                            <span>{status}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
