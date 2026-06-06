import { History, X } from "lucide-react";
import type { RunHistory } from "@/lib/types";

type RunHistoryPanelProps = {
  open: boolean;
  history: RunHistory;
  loading?: boolean;
  onClose: () => void;
};

const statusTone: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  failed: "bg-rose-50 text-rose-700 ring-rose-200",
  running: "bg-amber-50 text-amber-700 ring-amber-200"
};

export function RunHistoryPanel({ open, history, loading = false, onClose }: RunHistoryPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <History size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">运行历史</h2>
                <div className="text-xs font-semibold text-slate-500">{history.runs.length} runs</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭运行历史">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!loading && history.runs.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              当前没有 run_history.json 记录。
            </div>
          ) : null}
          {history.runs.map((run) => (
            <article key={run.run_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{run.run_id}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {run.run_type}
                </span>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                    statusTone[run.status] ?? "bg-slate-50 text-slate-600 ring-slate-200"
                  }`}
                >
                  {run.status}
                </span>
                {run.is_fixture ? (
                  <span className="rounded-full bg-violet-50 px-2 py-1 text-xs font-bold text-violet-700 ring-1 ring-violet-200">
                    fixture
                  </span>
                ) : null}
              </div>
              <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                <div>
                  <dt className="text-slate-400">step</dt>
                  <dd className="mt-1 text-slate-950">{run.step ?? "-"}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">duration_seconds</dt>
                  <dd className="mt-1 text-slate-950">{run.duration_seconds}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">errors</dt>
                  <dd className="mt-1 text-slate-950">{run.errors.length}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">recoverable</dt>
                  <dd className="mt-1 text-slate-950">{String(run.recoverable)}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">retry_hint</dt>
                  <dd className="mt-1 text-slate-950">{run.retry_hint ?? "-"}</dd>
                </div>
              </dl>
              <div className="mt-3 text-xs font-semibold text-slate-500">
                {run.start_time} - {run.end_time}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {run.outputs.map((output) => (
                  <span key={output} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">
                    {output}
                  </span>
                ))}
              </div>
              <div className="mt-3 text-xs font-bold text-slate-400">failure_diagnostics</div>
              <pre className="mt-3 overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                {JSON.stringify(run.failure_diagnostics, null, 2)}
              </pre>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
