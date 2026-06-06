import { Check, GitCompareArrows, X, XCircle } from "lucide-react";
import type { RevisionDecision, SentenceIssue } from "@/lib/types";

type RevisionDiffPanelProps = {
  open: boolean;
  issues: SentenceIssue[];
  decisions: RevisionDecision[];
  loading?: boolean;
  decisionLoadingId?: string | null;
  onDecision: (issueId: string, decision: "accepted" | "rejected") => Promise<void>;
  onClose: () => void;
};

function decisionFor(issueId: string, decisions: RevisionDecision[]) {
  for (let index = decisions.length - 1; index >= 0; index -= 1) {
    if (decisions[index].issue_id === issueId) return decisions[index];
  }
  return undefined;
}

export function RevisionDiffPanel({
  open,
  issues,
  decisions,
  loading = false,
  decisionLoadingId = null,
  onDecision,
  onClose
}: RevisionDiffPanelProps) {
  if (!open) return null;

  const diffIssues = issues.filter((issue) => issue.revision_diff);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <GitCompareArrows size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">修订建议 diff</h2>
                <div className="text-xs font-semibold text-slate-500">{diffIssues.length} suggestions</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭修订建议">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!loading && diffIssues.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              review_report.json 当前没有可展示的 revision_diff。
            </div>
          ) : null}
          {diffIssues.map((issue) => {
            const diff = issue.revision_diff!;
            const latestDecision = decisionFor(issue.issue_id, decisions);
            return (
              <article key={issue.issue_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-black text-slate-950">{issue.issue_id}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                    {issue.issue_type}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    {diff.change_type}
                  </span>
                  <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                    human approval required
                  </span>
                  {latestDecision ? (
                    <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">
                      {latestDecision.decision}
                    </span>
                  ) : null}
                </div>

                <div className="grid gap-3 lg:grid-cols-2">
                  <div className="rounded-[8px] border border-rose-100 bg-rose-50 p-3">
                    <div className="mb-2 text-xs font-black uppercase text-rose-500">before</div>
                    <p className="text-sm font-semibold leading-6 text-slate-800">{diff.before}</p>
                  </div>
                  <div className="rounded-[8px] border border-emerald-100 bg-emerald-50 p-3">
                    <div className="mb-2 text-xs font-black uppercase text-emerald-600">after</div>
                    <p className="text-sm font-semibold leading-6 text-slate-800">{diff.after}</p>
                  </div>
                </div>

                <dl className="mt-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                  <div>
                    <dt className="text-slate-400">claim_id</dt>
                    <dd className="mt-1 font-mono text-slate-950">{diff.preserved_claim_id ?? "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">numbers</dt>
                    <dd className="mt-1 text-slate-950">{String(diff.preserved_numbers)}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">units</dt>
                    <dd className="mt-1 text-slate-950">{String(diff.preserved_units)}</dd>
                  </div>
                </dl>

                {diff.warnings.length ? (
                  <ul className="mt-4 space-y-1 text-xs font-semibold leading-5 text-amber-700">
                    {diff.warnings.map((warning) => (
                      <li key={warning}>- {warning}</li>
                    ))}
                  </ul>
                ) : null}

                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    className="secondary-button"
                    disabled={decisionLoadingId === issue.issue_id}
                    onClick={() => onDecision(issue.issue_id, "rejected")}
                  >
                    <XCircle size={16} />
                    <span>Reject</span>
                  </button>
                  <button
                    className="primary-button"
                    disabled={decisionLoadingId === issue.issue_id}
                    onClick={() => onDecision(issue.issue_id, "accepted")}
                  >
                    <Check size={16} />
                    <span>Accept</span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
