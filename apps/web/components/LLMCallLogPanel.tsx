import { ScrollText, X } from "lucide-react";
import type { LLMCallLogEntry } from "@/lib/types";

type LLMCallLogPanelProps = {
  open: boolean;
  entries: LLMCallLogEntry[];
  loading?: boolean;
  onClose: () => void;
};

export function LLMCallLogPanel({ open, entries, loading = false, onClose }: LLMCallLogPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ScrollText size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">LLM Call Log</h2>
                <div className="text-xs font-semibold text-slate-500">{entries.length} calls</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close LLM Call Log">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {!loading && entries.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              No LLM calls have been logged for this project.
            </div>
          ) : null}
          {entries.map((entry) => (
            <article key={entry.call_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{entry.call_id}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {entry.operation}
                </span>
                <span className="rounded-full bg-cyan-50 px-2 py-1 text-xs font-bold text-cyan-700 ring-1 ring-cyan-200">
                  {entry.mode}
                </span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                  {entry.prompt_version}
                </span>
              </div>
              <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                <div>
                  <dt className="text-slate-400">provider</dt>
                  <dd className="mt-1 text-slate-950">{entry.provider}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">model</dt>
                  <dd className="mt-1 text-slate-950">{entry.model}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">status</dt>
                  <dd className="mt-1 text-slate-950">{entry.status}</dd>
                </div>
              </dl>
              <pre className="mt-3 max-h-[220px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                {JSON.stringify(
                  {
                    request_summary: entry.request_summary,
                    response_summary: entry.response_summary,
                    usage: entry.usage,
                    metadata: entry.metadata,
                    error: entry.error
                  },
                  null,
                  2
                )}
              </pre>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
