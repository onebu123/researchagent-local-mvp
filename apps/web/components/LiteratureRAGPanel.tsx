import { BookOpenCheck, Play, SearchCheck, X } from "lucide-react";
import { useState } from "react";
import type { LiteratureRAGAnswer, LiteratureRAGChunk, LiteratureRAGIndex } from "@/lib/types";

type LiteratureRAGPanelProps = {
  open: boolean;
  index?: LiteratureRAGIndex;
  chunks: LiteratureRAGChunk[];
  answers: LiteratureRAGAnswer[];
  loading?: boolean;
  actionLoading?: boolean;
  onBuild: () => Promise<void>;
  onAsk: (question: string) => Promise<void>;
  onClose: () => void;
};

export function LiteratureRAGPanel({
  open,
  index,
  chunks,
  answers,
  loading = false,
  actionLoading = false,
  onBuild,
  onAsk,
  onClose
}: LiteratureRAGPanelProps) {
  const [question, setQuestion] = useState("What does the demo literature mention about efficiency?");
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <SearchCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Literature RAG</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {chunks.length} chunks / {answers.length} answers
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Literature RAG">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="flex flex-wrap gap-2">
            <button className="secondary-button" onClick={onBuild} disabled={actionLoading}>
              <BookOpenCheck size={16} />
              <span>{actionLoading ? "Building" : "Build Index"}</span>
            </button>
          </div>
          {index ? (
            <div className="grid gap-3 sm:grid-cols-4">
              {[
                ["retrieval_mode", index.retrieval_mode],
                ["prompt_version", index.prompt_version],
                ["chunk_count", String(index.chunk_count)],
                ["optional_paperqa2_enabled", String(index.optional_paperqa2_enabled)]
              ].map(([label, value]) => (
                <div key={label} className="rounded-[8px] border border-slate-200 p-3">
                  <div className="text-xs font-bold text-slate-400">{label}</div>
                  <div className="mt-1 break-all text-sm font-black text-slate-950">{value}</div>
                </div>
              ))}
            </div>
          ) : null}
          <article className="rounded-[8px] border border-slate-200 p-4">
            <h3 className="text-sm font-black text-slate-950">Ask Literature</h3>
            <textarea
              className="mt-3 min-h-[84px] w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <div className="mt-3 flex justify-end">
              <button className="primary-button" onClick={() => onAsk(question)} disabled={actionLoading}>
                <Play size={16} />
                <span>Ask</span>
              </button>
            </div>
          </article>
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="space-y-3">
              <h3 className="text-sm font-black text-slate-950">Answers</h3>
              {answers.map((answer) => (
                <article key={answer.answer_id} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="font-mono text-xs font-black text-slate-950">{answer.answer_id}</div>
                  <div className="mt-2 text-sm font-semibold text-slate-700">{answer.question}</div>
                  <p className="mt-2 text-sm font-semibold leading-6 text-slate-600">{answer.answer}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {answer.source_passages.map((passage) => (
                      <span key={passage.chunk_id} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">
                        {passage.chunk_id}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </section>
            <section className="space-y-3">
              <h3 className="text-sm font-black text-slate-950">Chunks</h3>
              {chunks.slice(0, 6).map((chunk) => (
                <article key={chunk.chunk_id} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="font-mono text-xs font-black text-slate-950">{chunk.chunk_id}</div>
                  <div className="mt-1 break-all text-xs font-semibold text-slate-500">{chunk.source_file}</div>
                  <p className="mt-2 line-clamp-4 text-sm font-semibold leading-6 text-slate-600">{chunk.text}</p>
                </article>
              ))}
            </section>
          </div>
        </div>
      </section>
    </div>
  );
}
