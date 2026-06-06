import { ClipboardCheck, ShieldCheck, X } from "lucide-react";
import type { EvidenceClaim, EvidenceStatus } from "@/lib/types";

type EvidencePanelProps = {
  open: boolean;
  claims: EvidenceClaim[];
  loading?: boolean;
  onOpenClaimReview?: () => void;
  onClose: () => void;
};

const statusTone: Record<EvidenceStatus, string> = {
  supported: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  partial: "bg-amber-50 text-amber-700 ring-amber-200",
  missing: "bg-rose-50 text-rose-700 ring-rose-200",
  needs_human_review: "bg-sky-50 text-sky-700 ring-sky-200"
};

export function EvidencePanel({
  open,
  claims,
  loading = false,
  onOpenClaimReview,
  onClose
}: EvidencePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-3xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ShieldCheck size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Evidence 详情</h2>
                <div className="text-xs font-semibold text-slate-500">{claims.length} 条 claim</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {onOpenClaimReview ? (
                <button className="secondary-button" onClick={onOpenClaimReview} aria-label="Evidence Claim Review">
                  <ClipboardCheck size={15} />
                  <span>Review Claims</span>
                </button>
              ) : null}
              <button className="icon-button" onClick={onClose} aria-label="关闭 Evidence 详情">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!loading && claims.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              暂无 evidence.json 内容。
            </div>
          ) : null}
          {claims.map((claim) => (
            <article key={claim.claim_id} className="rounded-[8px] border border-slate-200 bg-slate-50/60 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{claim.claim_id}</span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                  {claim.section}
                </span>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                    statusTone[claim.evidence_status] ?? statusTone.needs_human_review
                  }`}
                >
                  {claim.evidence_status}
                </span>
              </div>
              <p className="text-sm font-semibold leading-6 text-slate-800">{claim.claim}</p>
              <dl className="mt-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                <div>
                  <dt className="text-slate-400">evidence_type</dt>
                  <dd className="mt-1 break-all text-slate-900">{claim.evidence_type}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">data_file</dt>
                  <dd className="mt-1 break-all text-slate-900">{claim.data_file ?? "-"}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">figure_file</dt>
                  <dd className="mt-1 break-all text-slate-900">{claim.figure_file ?? "-"}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">analysis_provenance_file</dt>
                  <dd className="mt-1 break-all text-slate-900">
                    {claim.analysis_provenance_file ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">human_verified</dt>
                  <dd className="mt-1 text-slate-900">{claim.human_verified ? "true" : "false"}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
