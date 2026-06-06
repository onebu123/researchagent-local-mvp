import { Activity, X } from "lucide-react";
import type { AnalysisProvenance } from "@/lib/types";

type AnalysisProvenancePanelProps = {
  open: boolean;
  provenance: AnalysisProvenance;
  loading?: boolean;
  onClose: () => void;
};

export function AnalysisProvenancePanel({
  open,
  provenance,
  loading = false,
  onClose
}: AnalysisProvenancePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-3xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <Activity size={20} className="text-[#12b5cb]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">分析来源</h2>
                <div className="text-xs font-semibold text-slate-500">{provenance.analysis_id}</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭分析来源">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          <dl className="grid gap-3 text-sm font-semibold text-slate-600 sm:grid-cols-2">
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <dt className="text-xs text-slate-400">input_data_file</dt>
              <dd className="mt-1 break-all font-mono text-slate-950">{provenance.input_data_file}</dd>
            </div>
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <dt className="text-xs text-slate-400">input_data_hash</dt>
              <dd className="mt-1 break-all font-mono text-slate-950">{provenance.input_data_hash}</dd>
            </div>
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <dt className="text-xs text-slate-400">analysis_function</dt>
              <dd className="mt-1 break-all font-mono text-slate-950">{provenance.analysis_function}</dd>
            </div>
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <dt className="text-xs text-slate-400">rows / columns</dt>
              <dd className="mt-1 text-slate-950">
                {provenance.row_count} / {provenance.column_count}
              </dd>
            </div>
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <dt className="text-xs text-slate-400">python_version</dt>
              <dd className="mt-1 text-slate-950">{provenance.runtime.python_version ?? "-"}</dd>
            </div>
            <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
              <dt className="text-xs text-slate-400">pandas / numpy</dt>
              <dd className="mt-1 text-slate-950">
                {provenance.runtime.pandas_version ?? "-"} / {provenance.runtime.numpy_version ?? "-"}
              </dd>
            </div>
          </dl>

          <section>
            <h3 className="mb-2 text-sm font-black text-slate-950">parameters</h3>
            <pre className="overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
              {JSON.stringify(provenance.parameters ?? {}, null, 2)}
            </pre>
          </section>

          <section>
            <h3 className="mb-2 text-sm font-black text-slate-950">script_version / random_seed</h3>
            <pre className="overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
              {JSON.stringify(
                {
                  script_version: provenance.script_version ?? {},
                  random_seed: provenance.random_seed ?? null,
                  random_seed_note: provenance.random_seed_note ?? ""
                },
                null,
                2
              )}
            </pre>
          </section>

          <section>
            <h3 className="mb-2 text-sm font-black text-slate-950">generated_files</h3>
            <div className="flex flex-wrap gap-2">
              {provenance.generated_files.map((file) => (
                <span key={file} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">
                  {file}
                </span>
              ))}
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-sm font-black text-slate-950">output_file_hashes</h3>
            <pre className="overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
              {JSON.stringify(provenance.output_file_hashes ?? {}, null, 2)}
            </pre>
          </section>

          <section>
            <h3 className="mb-2 text-sm font-black text-slate-950">limitations</h3>
            <ul className="space-y-2 text-sm font-semibold leading-6 text-slate-700">
              {provenance.limitations.map((item) => (
                <li key={item}>- {item}</li>
              ))}
            </ul>
          </section>
        </div>
      </section>
    </div>
  );
}
