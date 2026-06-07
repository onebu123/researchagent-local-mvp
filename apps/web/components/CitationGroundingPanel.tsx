import { Link2, X } from "lucide-react";
import type { CitationGroundingReport } from "@/lib/types";

type CitationGroundingPanelProps = {
  open: boolean;
  report: CitationGroundingReport;
  loading?: boolean;
  onClose: () => void;
};

const tone: Record<string, string> = {
  strong: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  moderate: "bg-cyan-50 text-cyan-700 ring-cyan-200",
  weak: "bg-amber-50 text-amber-700 ring-amber-200",
  unsupported: "bg-rose-50 text-rose-700 ring-rose-200",
  needs_human_review: "bg-amber-50 text-amber-700 ring-amber-200"
};

export function CitationGroundingPanel({
  open,
  report,
  loading = false,
  onClose
}: CitationGroundingPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <Link2 size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Citation Grounding</h2>
                <div className="text-xs font-semibold text-slate-500">{report.summary.total ?? report.items.length} checked claims</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Citation Grounding">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <dl className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-3 lg:grid-cols-6">
            {Object.entries(report.summary).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                <dt>{key}</dt>
                <dd className="font-mono text-slate-950">{value}</dd>
              </div>
            ))}
          </dl>
          {report.items.map((item) => (
            <article key={item.grounding_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{item.grounding_id}</span>
                <span className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${tone[item.grounding_strength] ?? tone.needs_human_review}`}>
                  {item.grounding_strength}
                </span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                  {item.candidate_chunk_id ?? "no_chunk"}
                </span>
              </div>
              <p className="text-sm font-semibold leading-6 text-slate-700">{item.claim}</p>
              <blockquote className="mt-3 rounded-[8px] bg-slate-50 p-3 text-xs font-semibold leading-5 text-slate-700">
                {item.text_excerpt || "No local passage excerpt."}
              </blockquote>
              <pre className="mt-3 max-h-[180px] overflow-auto rounded-[8px] bg-white p-3 text-xs font-semibold text-slate-800 ring-1 ring-slate-200">
                {JSON.stringify(item.signals, null, 2)}
              </pre>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
