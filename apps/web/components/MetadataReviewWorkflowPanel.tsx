import { ClipboardCheck, X } from "lucide-react";
import type {
  LiteratureMetadataDiffReport,
  MetadataReviewActionValue,
  MetadataReviewActionsResponse
} from "@/lib/types";

type MetadataReviewWorkflowPanelProps = {
  open: boolean;
  diffReport: LiteratureMetadataDiffReport;
  reviewState: MetadataReviewActionsResponse;
  loading?: boolean;
  actionLoading?: boolean;
  onOpenRevertPreview?: () => void;
  onReview: (
    literatureId: string,
    field: string,
    action: MetadataReviewActionValue,
    sourceHistoryId: string
  ) => Promise<void>;
  onClose: () => void;
};

const actions: MetadataReviewActionValue[] = [
  "accept_change",
  "reject_change",
  "needs_verification",
  "request_revert"
];

export function MetadataReviewWorkflowPanel({
  open,
  diffReport,
  reviewState,
  loading = false,
  actionLoading = false,
  onOpenRevertPreview,
  onReview,
  onClose
}: MetadataReviewWorkflowPanelProps) {
  if (!open) return null;

  const latest = new Map(
    reviewState.summary.records.map((record) => [
      `${record.literature_id}:${record.field}`,
      record
    ])
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ClipboardCheck size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Metadata Review Workflow</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {reviewState.summary.summary.total_actions} recorded actions
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {onOpenRevertPreview ? (
                <button className="secondary-button" onClick={onOpenRevertPreview} aria-label="Metadata Revert Preview">
                  <ClipboardCheck size={15} />
                  <span>Revert Preview</span>
                </button>
              ) : null}
              <button className="icon-button" onClick={onClose} aria-label="Close metadata review workflow">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          {diffReport.records.flatMap((record) =>
            record.changes.map((change) => {
              const key = `${record.literature_id}:${change.field}`;
              const review = latest.get(key);
              return (
                <article key={`${key}:${change.source_history_id}`} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-black text-slate-950">
                      {record.literature_id}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                      {change.field}
                    </span>
                    <span className="rounded-full bg-cyan-50 px-2 py-1 text-xs font-bold text-cyan-700 ring-1 ring-cyan-200">
                      {review?.latest_action ?? "unreviewed"}
                    </span>
                  </div>
                  <dl className="grid gap-3 text-xs font-semibold text-slate-600 md:grid-cols-3">
                    <div>
                      <dt className="text-slate-400">old_value</dt>
                      <dd className="mt-1 break-all font-mono text-slate-950">
                        {JSON.stringify(change.old_value)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">new_value</dt>
                      <dd className="mt-1 break-all font-mono text-slate-950">
                        {JSON.stringify(change.new_value)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">source_history_id</dt>
                      <dd className="mt-1 break-all font-mono text-slate-950">
                        {change.source_history_id ?? "-"}
                      </dd>
                    </div>
                  </dl>
                  <div className="mt-3 text-xs font-semibold text-slate-600">
                    revert: {change.revert_suggestion.can_revert ? "available" : "unavailable"} /{" "}
                    {change.revert_suggestion.warning}
                  </div>
                  {change.source_history_id ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {actions.map((action) => (
                        <button
                          key={action}
                          className="secondary-button"
                          disabled={actionLoading}
                          onClick={() =>
                            onReview(record.literature_id, change.field, action, change.source_history_id ?? "")
                          }
                        >
                          <ClipboardCheck size={15} />
                          <span>{action}</span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </article>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
