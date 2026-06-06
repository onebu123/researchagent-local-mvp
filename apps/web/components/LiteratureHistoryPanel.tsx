import { BookOpenCheck, X } from "lucide-react";
import type { LiteratureHistoryEntry } from "@/lib/types";

type LiteratureHistoryPanelProps = {
  open: boolean;
  history: LiteratureHistoryEntry[];
  loading?: boolean;
  onClose: () => void;
};

export function LiteratureHistoryPanel({
  open,
  history,
  loading = false,
  onClose
}: LiteratureHistoryPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BookOpenCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">文献 metadata 变更历史</h2>
                <div className="text-xs font-semibold text-slate-500">{history.length} records</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭文献历史">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!loading && history.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              当前没有 metadata_history.jsonl 记录。
            </div>
          ) : null}
          {history.map((entry) => (
            <article key={entry.history_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{entry.history_id}</span>
                <span className="font-mono text-xs font-bold text-slate-600">{entry.literature_id}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {entry.source}
                </span>
              </div>
              <div className="mb-3 text-xs font-semibold text-slate-500">{entry.changed_at}</div>
              <div className="mb-3 flex flex-wrap gap-2">
                {entry.changed_fields.map((field) => (
                  <span key={field} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">
                    {field}
                  </span>
                ))}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <pre className="overflow-x-auto rounded-[8px] bg-rose-50 p-3 text-xs font-semibold text-rose-900">
                  {JSON.stringify(entry.old_values, null, 2)}
                </pre>
                <pre className="overflow-x-auto rounded-[8px] bg-emerald-50 p-3 text-xs font-semibold text-emerald-900">
                  {JSON.stringify(entry.new_values, null, 2)}
                </pre>
              </div>
              <div className="mt-3 text-xs font-semibold text-slate-500">{entry.reason}</div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
