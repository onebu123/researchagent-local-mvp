import { CheckCircle2, CircleHelp, XCircle } from "lucide-react";
import type { IssueResolutionReview } from "@/lib/types";

type IssueResolutionReviewPanelProps = {
  versionId: string;
  issueIds: string[];
  latestReviews?: IssueResolutionReview[];
  loadingId?: string | null;
  onReview?: (
    issueId: string,
    versionId: string,
    status: "resolved" | "unresolved" | "needs_review"
  ) => Promise<void>;
};

export function IssueResolutionReviewPanel({
  versionId,
  issueIds,
  latestReviews = [],
  loadingId,
  onReview
}: IssueResolutionReviewPanelProps) {
  if (!issueIds.length) {
    return (
      <div className="rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-500">
        No issues in this bucket.
      </div>
    );
  }

  const reviewByIssue = new Map(latestReviews.map((review) => [review.issue_id, review]));

  return (
    <div className="space-y-2">
      {issueIds.map((issueId) => {
        const latest = reviewByIssue.get(issueId);
        const busy = loadingId === `${versionId}:${issueId}`;
        return (
          <div
            key={issueId}
            className="rounded-[8px] border border-slate-200 bg-white p-3 text-xs font-semibold text-slate-600"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono font-black text-slate-950">{issueId}</span>
              {latest ? (
                <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-700 ring-1 ring-slate-200">
                  human={latest.human_status}
                </span>
              ) : null}
            </div>
            {latest ? (
              <div className="mt-2 font-mono text-[11px] text-slate-500">
                auto={latest.auto_status} / {latest.reason || "no reason"}
              </div>
            ) : null}
            {onReview ? (
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => onReview(issueId, versionId, "resolved")}
                >
                  <CheckCircle2 size={14} />
                  <span>Resolved</span>
                </button>
                <button
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => onReview(issueId, versionId, "unresolved")}
                >
                  <XCircle size={14} />
                  <span>Unresolved</span>
                </button>
                <button
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => onReview(issueId, versionId, "needs_review")}
                >
                  <CircleHelp size={14} />
                  <span>Review</span>
                </button>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
