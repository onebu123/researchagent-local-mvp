import { FileSearch, X } from "lucide-react";
import type { PDFPageTextPreviewResponse } from "@/lib/types";

type PDFPageTextPreviewPanelProps = {
  open: boolean;
  preview: PDFPageTextPreviewResponse;
  loading?: boolean;
  onClose: () => void;
};

export function PDFPageTextPreviewPanel({
  open,
  preview,
  loading = false,
  onClose
}: PDFPageTextPreviewPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileSearch size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">PDF Page Text Preview</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {preview.summary.page_count} pages / OCR {String(preview.summary.ocr_attempted)}
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close PDF page text preview">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {preview.pages.map((page) => (
            <article key={`${page.source_file}:${page.page_number}`} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="break-all font-mono text-sm font-black text-slate-950">
                  {page.source_file}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  page {page.page_number}
                </span>
                <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700 ring-1 ring-indigo-200">
                  {page.auto_quality_signal}
                </span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                  {page.human_status}
                </span>
              </div>
              <pre className="whitespace-pre-wrap rounded-[8px] bg-slate-50 p-3 text-sm font-semibold leading-6 text-slate-800">
                {page.text_preview || "(empty)"}
              </pre>
              <div className="mt-3 text-xs font-semibold text-slate-500">
                char_count={page.char_count} / parse_status={page.parse_status} / ocr_attempted={String(page.ocr_attempted)}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
