import { ClipboardCheck, X } from "lucide-react";
import type {
  RevisionDiffHumanStatus,
  RevisionDiffReviewsResponse,
  RevisionLineDiff
} from "@/lib/types";

type RevisionDiffReviewPanelProps = {
  open: boolean;
  diffs: RevisionLineDiff[];
  reviewState: RevisionDiffReviewsResponse;
  loading?: boolean;
  actionLoading?: boolean;
  onReview: (
    revisionDiffId: string,
    changeId: string,
    status: RevisionDiffHumanStatus
  ) => Promise<void>;
  onClose: () => void;
};

const statusOptions: RevisionDiffHumanStatus[] = [
  "accepted",
  "rejected",
  "needs_rewrite",
  "needs_evidence"
];

export function RevisionDiffReviewPanel({
  open,
  diffs,
  reviewState,
  loading = false,
  actionLoading = false,
  onReview,
  onClose
}: RevisionDiffReviewPanelProps) {
  if (!open) return null;

  const latestStatus = new Map(
    reviewState.summary.changes.map((change) => [
      `${change.revision_diff_id}:${change.change_id}`,
      change
    ])
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ClipboardCheck size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Revision Diff Review</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {reviewState.summary.summary.reviewed} reviewed /{" "}
                  {reviewState.summary.summary.total_changes} changes
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close revision diff review">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-3 sm:grid-cols-4">
            {statusOptions.map((status) => (
              <div key={status} className="rounded-[8px] border border-slate-200 p-3">
                <div className="text-xs font-bold uppercase text-slate-400">{status}</div>
                <div className="mt-1 text-xl font-black text-slate-950">
                  {reviewState.summary.summary[status]}
                </div>
              </div>
            ))}
          </div>

          {diffs.flatMap((diff) =>
            diff.changes.map((change) => {
              const key = `${diff.revision_diff_id}:${change.change_id}`;
              const review = latestStatus.get(key);
              return (
                <article key={key} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-black text-slate-950">
                      {diff.revision_diff_id} / {change.change_id}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                      {change.section}
                    </span>
                    <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700 ring-1 ring-indigo-200">
                      {review?.latest_human_status ?? "unreviewed"}
                    </span>
                  </div>
                  <dl className="mb-3 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-4">
                    <div>
                      <dt className="text-slate-400">paragraph</dt>
                      <dd className="mt-1 text-slate-950">{change.paragraph_index}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">sentence</dt>
                      <dd className="mt-1 text-slate-950">{change.sentence_index}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">line</dt>
                      <dd className="mt-1 text-slate-950">
                        {change.line_start}-{change.line_end}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">review_count</dt>
                      <dd className="mt-1 text-slate-950">{review?.review_count ?? 0}</dd>
                    </div>
                  </dl>
                  <div className="grid gap-3 lg:grid-cols-2">
                    <pre className="overflow-x-auto rounded-[8px] bg-rose-50 p-3 text-xs font-semibold text-rose-900">
                      {change.before || "-"}
                    </pre>
                    <pre className="overflow-x-auto rounded-[8px] bg-emerald-50 p-3 text-xs font-semibold text-emerald-900">
                      {change.after || "-"}
                    </pre>
                  </div>
                  <div className="mt-3 text-xs font-semibold text-slate-600">
                    issues: {change.related_issue_ids.join(", ") || "-"} / claims:{" "}
                    {change.related_claim_ids.join(", ") || "-"}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {statusOptions.map((status) => (
                      <button
                        key={status}
                        className="secondary-button"
                        disabled={actionLoading}
                        onClick={() => onReview(diff.revision_diff_id, change.change_id, status)}
                      >
                        <ClipboardCheck size={15} />
                        <span>{status}</span>
                      </button>
                    ))}
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
