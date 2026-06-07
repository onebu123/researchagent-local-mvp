import { BarChart3, RefreshCw, X } from "lucide-react";
import type { RAGChunkQualityReport, RAGRetrievalEvalReport, RAGRetrievalEvalSet } from "@/lib/types";

type RAGQualityPanelProps = {
  open: boolean;
  quality: RAGChunkQualityReport;
  evalSet: RAGRetrievalEvalSet;
  evaluation: RAGRetrievalEvalReport;
  loading?: boolean;
  actionLoading?: boolean;
  onEvaluate: () => Promise<void>;
  onClose: () => void;
};

export function RAGQualityPanel({
  open,
  quality,
  evalSet,
  evaluation,
  loading = false,
  actionLoading = false,
  onEvaluate,
  onClose
}: RAGQualityPanelProps) {
  if (!open) return null;

  const metricItems = [
    ["hit_at_1", evaluation.metrics.hit_at_1 ?? 0],
    ["hit_at_3", evaluation.metrics.hit_at_3 ?? 0],
    ["mean_reciprocal_rank", evaluation.metrics.mean_reciprocal_rank ?? 0],
    ["total_cases", evaluation.metrics.total_cases ?? 0]
  ];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BarChart3 size={20} className="text-[#2f6fed]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">RAG Quality</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {quality.summary.total_chunks ?? 0} chunks / {evalSet.cases.length} eval cases
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close RAG Quality">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="flex flex-wrap gap-2">
            <button className="secondary-button" onClick={onEvaluate} disabled={actionLoading}>
              <RefreshCw size={16} />
              <span>{actionLoading ? "Evaluating" : "Run Retrieval Eval"}</span>
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            {metricItems.map(([label, value]) => (
              <div key={label} className="rounded-[8px] border border-slate-200 p-3">
                <div className="text-xs font-bold text-slate-400">{label}</div>
                <div className="mt-1 text-sm font-black text-slate-950">{String(value)}</div>
              </div>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="space-y-3">
              <h3 className="text-sm font-black text-slate-950">Chunk Quality</h3>
              {quality.items.slice(0, 8).map((item) => (
                <article key={item.chunk_id} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-mono text-xs font-black text-slate-950">{item.chunk_id}</div>
                    <span className="rounded bg-slate-50 px-2 py-1 text-xs font-black text-slate-700 ring-1 ring-slate-200">
                      {item.quality_status} / {item.quality_score}
                    </span>
                  </div>
                  <div className="mt-1 break-all text-xs font-semibold text-slate-500">{item.source_file}</div>
                  <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-3">
                    <span>{item.token_count} tokens</span>
                    <span>{item.character_count} chars</span>
                    <span>diversity {item.lexical_diversity}</span>
                  </div>
                  {item.warnings.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.warnings.map((warning) => (
                        <span key={warning} className="rounded bg-amber-50 px-2 py-1 text-xs font-bold text-amber-800">
                          {warning}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))}
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-black text-slate-950">Retrieval Evaluation</h3>
              {evaluation.results.map((result) => (
                <article key={result.case_id} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="font-mono text-xs font-black text-slate-950">{result.case_id}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{result.query}</div>
                  <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                    <span>rank {result.rank ?? "miss"}</span>
                    <span>top score {result.top_score}</span>
                    <span>hit@1 {String(result.hit_at_1)}</span>
                    <span>hit@3 {String(result.hit_at_3)}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {result.top_chunk_ids.map((chunkId) => (
                      <span key={chunkId} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">
                        {chunkId}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </section>
          </div>
          <div className="rounded-[8px] border border-slate-200 p-4 text-xs font-semibold leading-6 text-slate-500">
            {evaluation.limitations.join(" ")}
          </div>
        </div>
      </section>
    </div>
  );
}
