import { Play, SearchCheck, X } from "lucide-react";
import type {
  ReferenceVerificationProvider,
  ReferenceVerificationResult,
  ReferenceVerificationSummaryResponse
} from "@/lib/types";

type ReferenceVerificationPanelProps = {
  open: boolean;
  results: ReferenceVerificationResult[];
  summary: ReferenceVerificationSummaryResponse;
  provider: ReferenceVerificationProvider;
  loading?: boolean;
  actionLoading?: boolean;
  onProviderChange: (provider: ReferenceVerificationProvider) => void;
  onRun: () => Promise<void>;
  onClose: () => void;
};

const tone: Record<string, string> = {
  verified_candidate: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  ambiguous_match: "bg-cyan-50 text-cyan-700 ring-cyan-200",
  needs_human_review: "bg-amber-50 text-amber-700 ring-amber-200",
  no_match: "bg-rose-50 text-rose-700 ring-rose-200",
  provider_failed: "bg-slate-100 text-slate-700 ring-slate-200"
};

function textValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "missing";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "missing";
  return String(value);
}

export function ReferenceVerificationPanel({
  open,
  results,
  summary,
  provider,
  loading = false,
  actionLoading = false,
  onProviderChange,
  onRun,
  onClose
}: ReferenceVerificationPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <SearchCheck size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Reference Verification</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {summary.total_records} records / {summary.summary.needs_human_review ?? 0} need review
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Reference Verification">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="flex flex-wrap items-center gap-3">
            <select
              className="rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-bold text-slate-950"
              value={provider}
              onChange={(event) => onProviderChange(event.target.value as ReferenceVerificationProvider)}
            >
              <option value="mock_fixture">mock_fixture</option>
              <option value="crossref_optional">crossref_optional</option>
              <option value="semantic_scholar_optional">semantic_scholar_optional</option>
              <option value="openalex_optional">openalex_optional</option>
              <option value="arxiv_optional">arxiv_optional</option>
              <option value="pubmed_optional">pubmed_optional</option>
            </select>
            <button className="primary-button" onClick={onRun} disabled={actionLoading}>
              <Play size={16} />
              <span>{actionLoading ? "Running" : "Run Reference Verification"}</span>
            </button>
            <span className="rounded-full bg-slate-50 px-3 py-2 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
              literature_index_modified=false
            </span>
          </div>

          <dl className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-3 lg:grid-cols-6">
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
                  <span className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${tone[record.status] ?? tone.needs_human_review}`}>
                    {record.status}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    {record.provider}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    confidence={record.match_scores.overall_confidence}
                  </span>
                </div>
                <div className="grid gap-3 text-sm md:grid-cols-2">
                  <div>
                    <div className="text-xs font-black uppercase text-slate-400">Query</div>
                    <div className="mt-1 font-bold text-slate-950">{textValue(record.query.title)}</div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">
                      DOI {textValue(record.query.doi)} / year {textValue(record.query.year)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-black uppercase text-slate-400">Candidate</div>
                    <div className="mt-1 font-bold text-slate-950">{textValue(record.candidate.title)}</div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">
                      DOI {textValue(record.candidate.doi)} / year {textValue(record.candidate.year)}
                    </div>
                  </div>
                </div>
                {record.warnings.length ? (
                  <div className="mt-3 rounded bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800 ring-1 ring-amber-200">
                    {record.warnings.join(" ")}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
