import { CheckCircle2, ClipboardCheck, X, XCircle } from "lucide-react";
import type {
  ReferenceApproval,
  ReferenceApprovalDecision,
  ReferenceApprovalSummaryResponse,
  ReferenceVerificationResult
} from "@/lib/types";

type ReferenceApprovalPanelProps = {
  open: boolean;
  results: ReferenceVerificationResult[];
  approvals: ReferenceApproval[];
  summary: ReferenceApprovalSummaryResponse;
  loading?: boolean;
  actionLoading?: boolean;
  onDecision: (
    verificationId: string,
    decision: ReferenceApprovalDecision,
    applyToLiteratureIndex: boolean
  ) => Promise<void>;
  onClose: () => void;
};

export function ReferenceApprovalPanel({
  open,
  results,
  approvals,
  summary,
  loading = false,
  actionLoading = false,
  onDecision,
  onClose
}: ReferenceApprovalPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ClipboardCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Approval Workflow</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {summary.summary.total_records ?? approvals.length} decisions / {summary.summary.applied_to_literature_index ?? 0} applied
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Approval Workflow">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <dl className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-2 lg:grid-cols-5">
            {Object.entries(summary.summary).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                <dt>{key}</dt>
                <dd className="font-mono text-slate-950">{value}</dd>
              </div>
            ))}
          </dl>

          <div className="grid gap-3">
            {results.map((record) => (
              <article key={record.verification_id} className="rounded-[8px] border border-slate-200 p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-black text-slate-950">{record.verification_id}</span>
                  <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                    {record.status}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    applied={String(record.applied_to_literature_index)}
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-950">
                  {String(record.candidate.title ?? record.query.title ?? record.literature_id)}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="secondary-button"
                    disabled={actionLoading}
                    onClick={() => onDecision(record.verification_id, "approved", false)}
                  >
                    <CheckCircle2 size={16} />
                    <span>Approve Only</span>
                  </button>
                  <button
                    className="primary-button"
                    disabled={actionLoading}
                    onClick={() => onDecision(record.verification_id, "approved", true)}
                  >
                    <CheckCircle2 size={16} />
                    <span>Approve and Apply</span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={actionLoading}
                    onClick={() => onDecision(record.verification_id, "rejected", false)}
                  >
                    <XCircle size={16} />
                    <span>Reject</span>
                  </button>
                </div>
              </article>
            ))}
          </div>

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Decision Log</div>
            <div className="grid gap-2">
              {approvals.map((approval) => (
                <div key={approval.approval_id} className="rounded bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">
                  <span className="font-mono font-black text-slate-950">{approval.approval_id}</span>
                  <span> / {approval.verification_id} / {approval.decision}</span>
                  <span> / applied={String(approval.applied_to_literature_index)}</span>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}
