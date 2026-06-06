import { GitBranch, X } from "lucide-react";
import type { VersionLineage } from "@/lib/types";

type VersionLineagePanelProps = {
  open: boolean;
  lineage: VersionLineage;
  loading?: boolean;
  onClose: () => void;
};

export function VersionLineagePanel({
  open,
  lineage,
  loading = false,
  onClose
}: VersionLineagePanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <GitBranch size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Version Lineage</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {lineage.summary.nodes} nodes / {lineage.summary.edges} edges
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Version Lineage">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <article className="rounded-[8px] border border-slate-200 p-4">
            <dl className="grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-6">
              <div>
                <dt className="text-slate-400">versions</dt>
                <dd className="mt-1 text-slate-950">{lineage.summary.versions}</dd>
              </div>
              <div>
                <dt className="text-slate-400">patches</dt>
                <dd className="mt-1 text-slate-950">{lineage.summary.patches}</dd>
              </div>
              <div>
                <dt className="text-slate-400">merges</dt>
                <dd className="mt-1 text-slate-950">{lineage.summary.merges}</dd>
              </div>
              <div>
                <dt className="text-slate-400">diffs</dt>
                <dd className="mt-1 text-slate-950">{lineage.summary.diffs}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-slate-400">file</dt>
                <dd className="mt-1 font-mono text-slate-950">{lineage.relative_path}</dd>
              </div>
            </dl>
          </article>

          <div className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 text-sm font-black text-slate-950">Nodes</div>
              <div className="max-h-[520px] overflow-auto">
                <table className="w-full text-left text-xs font-semibold">
                  <thead className="sticky top-0 bg-white text-slate-400">
                    <tr>
                      <th className="py-2 pr-3">id</th>
                      <th className="py-2 pr-3">type</th>
                      <th className="py-2 pr-3">status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {lineage.nodes.map((node) => (
                      <tr key={`${node.type}:${node.id}`}>
                        <td className="py-2 pr-3 font-mono text-slate-950">{node.id}</td>
                        <td className="py-2 pr-3 text-slate-700">{node.type}</td>
                        <td className="py-2 pr-3 text-slate-500">{node.status ?? node.source_type ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 text-sm font-black text-slate-950">Edges</div>
              <div className="max-h-[520px] overflow-auto">
                <table className="w-full text-left text-xs font-semibold">
                  <thead className="sticky top-0 bg-white text-slate-400">
                    <tr>
                      <th className="py-2 pr-3">source</th>
                      <th className="py-2 pr-3">relation</th>
                      <th className="py-2 pr-3">target</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {lineage.edges.map((edge) => (
                      <tr key={`${edge.source}:${edge.relation}:${edge.target}`}>
                        <td className="py-2 pr-3 font-mono text-slate-950">{edge.source}</td>
                        <td className="py-2 pr-3 text-slate-700">{edge.relation}</td>
                        <td className="py-2 pr-3 font-mono text-slate-950">{edge.target}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </div>

          {lineage.warnings.length ? (
            <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
              <div className="mb-2 text-sm font-black text-amber-800">Warnings</div>
              <ul className="space-y-1 text-xs font-semibold text-amber-800">
                {lineage.warnings.map((warning) => (
                  <li key={warning}>- {warning}</li>
                ))}
              </ul>
            </article>
          ) : null}
        </div>
      </section>
    </div>
  );
}
