import { useState } from "react";
import { ClipboardCheck, ShieldCheck, X } from "lucide-react";
import type {
  EvidenceClaim,
  EvidenceClaimReviewStatus,
  EvidenceClaimReviewsResponse
} from "@/lib/types";

type EvidenceClaimReviewPanelProps = {
  open: boolean;
  claims: EvidenceClaim[];
  reviewState: EvidenceClaimReviewsResponse;
  loading?: boolean;
  actionLoading?: boolean;
  onReview: (claimId: string, status: EvidenceClaimReviewStatus, reason: string) => Promise<void>;
  onClose: () => void;
};

const statuses: EvidenceClaimReviewStatus[] = [
  "supported",
  "partially_supported",
  "unsupported",
  "needs_more_evidence"
];

export function EvidenceClaimReviewPanel({
  open,
  claims,
  reviewState,
  loading = false,
  actionLoading = false,
  onReview,
  onClose
}: EvidenceClaimReviewPanelProps) {
  const [statusByClaim, setStatusByClaim] = useState<Record<string, EvidenceClaimReviewStatus>>({});
  const [reasonByClaim, setReasonByClaim] = useState<Record<string, string>>({});

  if (!open) return null;

  const latest = new Map(reviewState.summary.claims.map((claim) => [claim.claim_id, claim]));

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ShieldCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Evidence Claim Review</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {reviewState.summary.summary.reviewed} reviewed / {reviewState.summary.summary.total_claims} claims
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close evidence claim review">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-3 sm:grid-cols-4">
            {statuses.map((status) => (
              <div key={status} className="rounded-[8px] border border-slate-200 p-3">
                <div className="text-xs font-bold uppercase text-slate-400">{status}</div>
                <div className="mt-1 text-xl font-black text-slate-950">
                  {reviewState.summary.summary[status]}
                </div>
              </div>
            ))}
          </div>

          {claims.map((claim) => {
            const review = latest.get(claim.claim_id);
            const status = statusByClaim[claim.claim_id] ?? "supported";
            const reason = reasonByClaim[claim.claim_id] ?? "Recorded from ResearchAgent dashboard.";
            return (
              <article key={claim.claim_id} className="rounded-[8px] border border-slate-200 p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-black text-slate-950">{claim.claim_id}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                    {claim.evidence_type}
                  </span>
                  <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">
                    {review?.latest_human_status ?? "unreviewed"}
                  </span>
                </div>
                <p className="text-sm font-semibold leading-6 text-slate-800">{claim.claim}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(review?.related_files ?? []).map((file) => (
                    <span key={file} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                      {file}
                    </span>
                  ))}
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-[220px_1fr_auto]">
                  <select
                    className="rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700"
                    value={status}
                    onChange={(event) =>
                      setStatusByClaim((current) => ({
                        ...current,
                        [claim.claim_id]: event.target.value as EvidenceClaimReviewStatus
                      }))
                    }
                  >
                    {statuses.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                  <input
                    className="rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700"
                    value={reason}
                    onChange={(event) =>
                      setReasonByClaim((current) => ({ ...current, [claim.claim_id]: event.target.value }))
                    }
                  />
                  <button
                    className="primary-button"
                    disabled={actionLoading}
                    onClick={() => onReview(claim.claim_id, status, reason)}
                  >
                    <ClipboardCheck size={16} />
                    <span>Record</span>
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
