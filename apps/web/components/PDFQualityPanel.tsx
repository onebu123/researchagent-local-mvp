import { FileText, X } from "lucide-react";
import type { LiteratureRecord } from "@/lib/types";

type PDFQualityPanelProps = {
  open: boolean;
  records: LiteratureRecord[];
  loading?: boolean;
  onClose: () => void;
};

const qualityTone: Record<string, string> = {
  good: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  medium: "bg-amber-50 text-amber-700 ring-amber-200",
  low: "bg-rose-50 text-rose-700 ring-rose-200",
  empty: "bg-rose-100 text-rose-800 ring-rose-300",
  failed: "bg-rose-100 text-rose-800 ring-rose-300"
};

export function PDFQualityPanel({
  open,
  records,
  loading = false,
  onClose
}: PDFQualityPanelProps) {
  if (!open) return null;

  const pdfRecords = records.filter((record) => record.source_type === "pdf");

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">PDF 页级质量</h2>
                <div className="text-xs font-semibold text-slate-500">{pdfRecords.length} PDF records</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 PDF 质量">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!loading && pdfRecords.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              当前项目没有 PDF 文献记录。
            </div>
          ) : null}
          {pdfRecords.map((record) => (
            <article key={record.literature_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{record.literature_id}</span>
                <span className="break-all font-mono text-xs font-bold text-slate-600">{record.source_file}</span>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                    qualityTone[record.quality_label ?? ""] ?? "bg-slate-50 text-slate-600 ring-slate-200"
                  }`}
                >
                  {record.quality_label ?? "-"} / {record.quality_score ?? "-"}
                </span>
              </div>
              <dl className="mb-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                <div>
                  <dt className="text-slate-400">page_count</dt>
                  <dd className="mt-1 text-slate-950">{record.page_count ?? "-"}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">empty_page_count</dt>
                  <dd className="mt-1 text-slate-950">{record.empty_page_count ?? "-"}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">parse_status</dt>
                  <dd className="mt-1 text-slate-950">{record.parse_status}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">manual_review</dt>
                  <dd className="mt-1 text-slate-950">{String(record.needs_manual_review ?? false)}</dd>
                </div>
              </dl>
              <div className="grid gap-3 md:grid-cols-2">
                {(record.pages ?? []).map((page) => (
                  <div key={`${record.literature_id}-${page.page_number}`} className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-black text-slate-950">page {page.page_number}</span>
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                          qualityTone[page.quality_signal] ?? "bg-slate-100 text-slate-700 ring-slate-200"
                        }`}
                      >
                        {page.quality_signal}
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-slate-600">
                      chars={page.char_count} / empty={String(page.empty)} / ocr={page.ocr.ocr_status}
                    </div>
                    {page.warnings.length ? (
                      <ul className="mt-2 space-y-1 text-xs font-semibold text-amber-700">
                        {page.warnings.map((warning) => (
                          <li key={warning}>- {warning}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
