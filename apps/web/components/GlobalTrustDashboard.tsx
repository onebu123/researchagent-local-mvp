import { AlertTriangle, FileCheck2, ShieldCheck, X } from "lucide-react";
import type {
  CitationGroundingReport,
  ManuscriptReferencesStatus,
  ReferenceApprovalSummaryResponse,
  ReferenceVerificationSummaryResponse,
  TrustSummary
} from "@/lib/types";

type GlobalTrustDashboardProps = {
  open: boolean;
  summary: TrustSummary;
  referenceVerificationSummary?: ReferenceVerificationSummaryResponse;
  referenceApprovalSummary?: ReferenceApprovalSummaryResponse;
  citationGrounding?: CitationGroundingReport;
  manuscriptReferencesStatus?: ManuscriptReferencesStatus;
  loading?: boolean;
  onOpenReadiness?: () => void;
  onClose: () => void;
};

export function GlobalTrustDashboard({
  open,
  summary,
  referenceVerificationSummary,
  referenceApprovalSummary,
  citationGrounding,
  manuscriptReferencesStatus,
  loading = false,
  onOpenReadiness,
  onClose
}: GlobalTrustDashboardProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ShieldCheck size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Global Trust Dashboard</h2>
                <div className="text-xs font-semibold text-slate-500">{summary.overall_status}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="secondary-button" onClick={onOpenReadiness}>
                <FileCheck2 size={16} />
                <span>v1.0 Readiness</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="Close trust dashboard">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {Object.entries(summary.scores).map(([key, value]) => (
              <div key={key} className="rounded-[8px] border border-slate-200 p-3">
                <div className="text-xs font-bold uppercase text-slate-400">{key}</div>
                <div className="mt-1 text-xl font-black text-slate-950">{Math.round(value * 100)}%</div>
              </div>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-black text-slate-950">
                <AlertTriangle size={17} className="text-amber-600" />
                <span>Blocking Issues</span>
              </div>
              <div className="space-y-2">
                {summary.blocking_issues.length === 0 ? (
                  <div className="text-sm font-semibold text-slate-500">No blocking issue recorded.</div>
                ) : null}
                {summary.blocking_issues.map((item) => (
                  <div key={`${item.item_type}:${item.item_id}`} className="rounded-[8px] bg-amber-50 p-3 text-sm font-semibold text-amber-900">
                    <div className="font-mono text-xs font-black">{item.item_type}:{item.item_id}</div>
                    <div className="mt-1">{item.message}</div>
                  </div>
                ))}
              </div>
            </article>

            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 text-sm font-black text-slate-950">Counts</div>
              <dl className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                {Object.entries(summary.counts).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                    <dt>{key}</dt>
                    <dd className="font-mono text-slate-950">{value}</dd>
                  </div>
                ))}
              </dl>
            </article>
          </div>

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Reference Trust</div>
            <dl className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-2 lg:grid-cols-4">
              <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                <dt>verification_needs_review</dt>
                <dd className="font-mono text-slate-950">
                  {referenceVerificationSummary?.summary.needs_human_review ?? 0}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                <dt>approvals_applied</dt>
                <dd className="font-mono text-slate-950">
                  {referenceApprovalSummary?.summary.applied_to_literature_index ?? 0}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                <dt>grounding_strong</dt>
                <dd className="font-mono text-slate-950">{citationGrounding?.summary.strong ?? 0}</dd>
              </div>
              <div className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                <dt>formal_references</dt>
                <dd className="font-mono text-slate-950">
                  {manuscriptReferencesStatus?.verified_references.length ?? 0}
                </dd>
              </div>
            </dl>
          </article>

          {summary.failed_run_diagnostics.length ? (
            <article className="rounded-[8px] border border-rose-200 bg-rose-50 p-4">
              <div className="mb-3 text-sm font-black text-rose-950">Failed Run Diagnostics</div>
              <div className="grid gap-2 md:grid-cols-2">
                {summary.failed_run_diagnostics.map((run) => (
                  <div key={run.run_id ?? run.failed_step ?? "failed_run"} className="rounded-[8px] bg-white p-3 text-xs font-semibold text-rose-900 ring-1 ring-rose-200">
                    <div className="font-mono font-black">{run.run_id ?? "unknown_run"}</div>
                    <div className="mt-1">{run.failed_step ?? "unknown_step"}</div>
                    <div className="mt-1 leading-5">{run.likely_cause ?? "No likely cause recorded."}</div>
                    {run.is_fixture ? (
                      <span className="mt-2 inline-flex rounded-full bg-rose-100 px-2 py-1 text-[11px] font-black text-rose-700 ring-1 ring-rose-200">
                        fixture
                      </span>
                    ) : null}
                  </div>
                ))}
              </div>
            </article>
          ) : null}

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Open Items</div>
            <div className="grid gap-2 md:grid-cols-2">
              {summary.open_items.map((item) => (
                <div key={`${item.item_type}:${item.item_id}:${item.status}`} className="rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-700">
                  <div className="font-mono font-black text-slate-950">{item.item_type}:{item.item_id}</div>
                  <div className="mt-1">{item.status}</div>
                  <div className="mt-1 leading-5">{item.message}</div>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}
