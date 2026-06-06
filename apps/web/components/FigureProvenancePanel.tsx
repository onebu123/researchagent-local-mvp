import { LineChart, X } from "lucide-react";
import type { FigureProvenanceRecord } from "@/lib/types";

type FigureProvenancePanelProps = {
  open: boolean;
  records: FigureProvenanceRecord[];
  loading?: boolean;
  onClose: () => void;
};

export function FigureProvenancePanel({
  open,
  records,
  loading = false,
  onClose
}: FigureProvenancePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-3xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <LineChart size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">图表来源</h2>
                <div className="text-xs font-semibold text-slate-500">{records.length} 条 provenance</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭图表来源">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!loading && records.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              暂无 figure_provenance.json 内容。
            </div>
          ) : null}
          {records.map((record) => (
            <article key={record.figure_id} className="rounded-[8px] border border-slate-200 bg-slate-50/60 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{record.figure_id}</span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                  {record.figure_type}
                </span>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                    record.is_ai_generated
                      ? "bg-rose-50 text-rose-700 ring-rose-200"
                      : "bg-emerald-50 text-emerald-700 ring-emerald-200"
                  }`}
                >
                  is_ai_generated={String(record.is_ai_generated)}
                </span>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                    record.is_experimental_result
                      ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                      : "bg-amber-50 text-amber-700 ring-amber-200"
                  }`}
                >
                  is_experimental_result={String(record.is_experimental_result)}
                </span>
              </div>
              <h3 className="text-sm font-black text-slate-950">{record.title}</h3>
              <dl className="mt-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                <div>
                  <dt className="text-slate-400">source_data</dt>
                  <dd className="mt-1 break-all text-slate-900">{record.source_data}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">data_hash</dt>
                  <dd className="mt-1 break-all font-mono text-slate-900">{record.data_hash}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-slate-400">output_files</dt>
                  <dd className="mt-1 flex flex-wrap gap-2">
                    {record.output_files.map((file) => (
                      <span key={file} className="rounded bg-white px-2 py-1 font-mono text-slate-900 ring-1 ring-slate-200">
                        {file}
                      </span>
                    ))}
                  </dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
