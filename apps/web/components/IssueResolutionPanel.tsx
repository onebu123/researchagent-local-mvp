import { CheckCircle2, X } from "lucide-react";
import type { IssueResolution } from "@/lib/types";
import { IssueResolutionReviewPanel } from "@/components/IssueResolutionReviewPanel";

type IssueResolutionPanelProps = {
  open: boolean;
  resolution: IssueResolution;
  loading?: boolean;
  reviewLoadingId?: string | null;
  onReview?: (
    issueId: string,
    versionId: string,
    status: "resolved" | "unresolved" | "needs_review"
  ) => Promise<void>;
  onClose: () => void;
};

export function IssueResolutionPanel({
  open,
  resolution,
  loading = false,
  reviewLoadingId,
  onReview,
  onClose
}: IssueResolutionPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <CheckCircle2 size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">查看 Issue Resolution</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {resolution.summary.total_sentence_issues} sentence issues
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 Issue Resolution">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          <article className="rounded-[8px] border border-slate-200 p-4">
            <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-5">
              <div>
                <dt className="text-slate-400">resolved</dt>
                <dd className="mt-1 text-slate-950">{resolution.summary.resolved}</dd>
              </div>
              <div>
                <dt className="text-slate-400">unresolved</dt>
                <dd className="mt-1 text-slate-950">{resolution.summary.unresolved}</dd>
              </div>
              <div>
                <dt className="text-slate-400">partial</dt>
                <dd className="mt-1 text-slate-950">{resolution.summary.partially_resolved}</dd>
              </div>
              <div>
                <dt className="text-slate-400">human_reviews</dt>
                <dd className="mt-1 text-slate-950">{resolution.summary.human_reviews ?? 0}</dd>
              </div>
              <div>
                <dt className="text-slate-400">generated_at</dt>
                <dd className="mt-1 font-mono text-slate-950">{resolution.generated_at}</dd>
              </div>
            </dl>
            <div className="mt-3 font-mono text-xs font-semibold text-slate-500">
              latest_human_status={JSON.stringify(resolution.summary.latest_human_status_counts ?? {})}
            </div>
            <p className="mt-3 text-xs font-semibold leading-5 text-slate-500">
              该视图只基于 patch/version provenance，不表示语义层面已经解决。
            </p>
          </article>

          {resolution.versions.map((version) => (
            <article key={version.version_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 font-mono text-sm font-black text-slate-950">
                {version.version_id}
              </div>
              <div className="mb-3 flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
                <span className="rounded-full bg-slate-100 px-2 py-1 ring-1 ring-slate-200">
                  source={version.source_type ?? "patch"}
                </span>
                {version.source_merge_id ? (
                  <span className="rounded-full bg-indigo-50 px-2 py-1 text-indigo-700 ring-1 ring-indigo-200">
                    merge={version.source_merge_id}
                  </span>
                ) : null}
                <span className="rounded-full bg-slate-100 px-2 py-1 ring-1 ring-slate-200">
                  human_reviewed={version.human_review_summary?.reviewed ?? 0}
                </span>
              </div>
              <div className="grid gap-3 lg:grid-cols-3">
                <div className="rounded-[8px] bg-emerald-50 p-3">
                  <div className="mb-2 text-xs font-black uppercase text-emerald-700">resolved</div>
                  <IssueResolutionReviewPanel
                    versionId={version.version_id}
                    issueIds={version.resolved_issue_ids}
                    latestReviews={version.latest_human_reviews}
                    loadingId={reviewLoadingId}
                    onReview={onReview}
                  />
                </div>
                <div className="rounded-[8px] bg-amber-50 p-3">
                  <div className="mb-2 text-xs font-black uppercase text-amber-700">partial</div>
                  <IssueResolutionReviewPanel
                    versionId={version.version_id}
                    issueIds={version.partially_resolved_issue_ids}
                    latestReviews={version.latest_human_reviews}
                    loadingId={reviewLoadingId}
                    onReview={onReview}
                  />
                </div>
                <div className="rounded-[8px] bg-rose-50 p-3">
                  <div className="mb-2 text-xs font-black uppercase text-rose-700">unresolved</div>
                  <IssueResolutionReviewPanel
                    versionId={version.version_id}
                    issueIds={version.unresolved_issue_ids}
                    latestReviews={version.latest_human_reviews}
                    loadingId={reviewLoadingId}
                    onReview={onReview}
                  />
                </div>
              </div>
              {version.notes.length ? (
                <ul className="mt-3 space-y-1 text-xs font-semibold text-slate-500">
                  {version.notes.map((note) => (
                    <li key={note}>- {note}</li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
