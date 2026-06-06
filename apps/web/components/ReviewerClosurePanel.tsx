import { GitPullRequestClosed, X } from "lucide-react";
import type { ReviewerClosureSummary } from "@/lib/types";

type ReviewerClosurePanelProps = {
  open: boolean;
  closure: ReviewerClosureSummary;
  loading?: boolean;
  onClose: () => void;
};

export function ReviewerClosurePanel({
  open,
  closure,
  loading = false,
  onClose
}: ReviewerClosurePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <GitPullRequestClosed size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Reviewer Closure</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {closure.summary.closed} closed / {closure.summary.total_sentence_issues} issues
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close reviewer closure">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {Object.entries(closure.summary)
              .filter(([key]) => key !== "total_sentence_issues")
              .map(([key, value]) => (
                <div key={key} className="rounded-[8px] border border-slate-200 p-3">
                  <div className="text-xs font-bold uppercase text-slate-400">{key}</div>
                  <div className="mt-1 text-xl font-black text-slate-950">{value}</div>
                </div>
              ))}
          </div>

          {closure.issues.map((issue) => (
            <article key={issue.issue_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{issue.issue_id}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {issue.severity}
                </span>
                <span className="rounded-full bg-cyan-50 px-2 py-1 text-xs font-bold text-cyan-700 ring-1 ring-cyan-200">
                  {issue.closure_status}
                </span>
              </div>
              <p className="text-sm font-semibold leading-6 text-slate-800">{issue.sentence}</p>
              <div className="mt-3 text-xs font-semibold leading-5 text-slate-600">{issue.reason}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {issue.linked_changes.map((change) => (
                  <span key={`${change.revision_diff_id}:${change.change_id}`} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                    {change.revision_diff_id}/{change.change_id}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
