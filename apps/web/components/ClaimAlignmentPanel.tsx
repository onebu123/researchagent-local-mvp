import { GitCompareArrows, X } from "lucide-react";
import type { ClaimAlignment } from "@/lib/types";

type ClaimAlignmentPanelProps = {
  open: boolean;
  alignment: ClaimAlignment;
  loading?: boolean;
  onClose: () => void;
};

const statusTone: Record<string, string> = {
  matched: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  needs_claim_alignment: "bg-amber-50 text-amber-700 ring-amber-200",
  not_claim: "bg-slate-100 text-slate-700 ring-slate-200"
};

export function ClaimAlignmentPanel({
  open,
  alignment,
  loading = false,
  onClose
}: ClaimAlignmentPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <GitCompareArrows size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Claim 对齐</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {alignment.alignment_status} · {alignment.summary.total_sentences_checked} sentences
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭 Claim 对齐">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          <div className="grid gap-3 sm:grid-cols-4">
            {[
              ["matched", alignment.summary.matched],
              ["needs", alignment.summary.needs_claim_alignment],
              ["not_claim", alignment.summary.not_claim],
              ["checked", alignment.summary.total_sentences_checked]
            ].map(([label, value]) => (
              <div key={label} className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-bold text-slate-500">{label}</div>
                <div className="mt-1 text-xl font-black text-slate-950">{value}</div>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            {alignment.aligned_claims.map((item) => (
              <article key={item.alignment_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-black text-slate-950">{item.alignment_id}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                    {item.section} · P{item.paragraph_index}/S{item.sentence_index}
                  </span>
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                      statusTone[item.match_status] ?? statusTone.not_claim
                    }`}
                  >
                    {item.match_status}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    {item.confidence}
                  </span>
                </div>
                <p className="text-sm font-semibold leading-6 text-slate-800">{item.sentence}</p>
                <dl className="mt-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                  <div>
                    <dt className="text-slate-400">matched_claim_id</dt>
                    <dd className="mt-1 font-mono text-slate-950">{item.matched_claim_id ?? "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">evidence_status</dt>
                    <dd className="mt-1 text-slate-950">{item.evidence_status}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-slate-400">notes</dt>
                    <dd className="mt-1 text-slate-950">{item.notes.join("; ") || "-"}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
