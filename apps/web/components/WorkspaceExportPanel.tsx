import { FileText, RefreshCw, ShieldCheck, X } from "lucide-react";
import type { WorkspaceExportManifest } from "@/lib/types";

type WorkspaceExportPanelProps = {
  open: boolean;
  manifest: WorkspaceExportManifest;
  loading?: boolean;
  actionLoading?: boolean;
  onCreate: () => Promise<void>;
  onRefresh: () => Promise<void>;
  onClose: () => void;
};

export function WorkspaceExportPanel({
  open,
  manifest,
  loading = false,
  actionLoading = false,
  onCreate,
  onRefresh,
  onClose
}: WorkspaceExportPanelProps) {
  if (!open) return null;

  const artifactCount = manifest.artifacts.filter((artifact) => artifact.available).length;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileText size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Workspace Export</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {manifest.available ? manifest.relative_path : manifest.message ?? "No export yet"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="secondary-button" disabled={loading} onClick={onRefresh}>
                <RefreshCw size={16} />
                <span>Refresh</span>
              </button>
              <button className="primary-button" disabled={actionLoading} onClick={onCreate}>
                <FileText size={16} />
                <span>Generate docs</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="Close workspace export">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-4 lg:grid-cols-3">
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="text-xs font-bold uppercase text-slate-400">artifacts</div>
              <div className="mt-2 text-2xl font-black text-slate-950">{artifactCount}</div>
              <div className="mt-1 text-xs font-semibold text-slate-500">{manifest.export_dir}</div>
            </article>
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="text-xs font-bold uppercase text-slate-400">secret scan</div>
              <div className="mt-2 text-2xl font-black text-slate-950">
                {String(manifest.safety.secret_scan_passed)}
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-500">
                {manifest.safety.warning_count} warnings
              </div>
            </article>
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="text-xs font-bold uppercase text-slate-400">paths</div>
              <div className="mt-2 text-2xl font-black text-slate-950">
                {String(manifest.safety.project_relative_paths_only)}
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-500">project-relative only</div>
            </article>
          </div>

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Generated Artifacts</div>
            <div className="grid gap-2">
              {manifest.artifacts.map((artifact) => (
                <div
                  key={artifact.relative_path}
                  className="grid gap-2 rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-600 md:grid-cols-[180px_minmax(0,1fr)_120px]"
                >
                  <div className="font-black text-slate-950">{artifact.artifact_type}</div>
                  <div className="break-all font-mono">{artifact.relative_path}</div>
                  <div className="text-right font-mono text-slate-950">{artifact.size_bytes} bytes</div>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-black text-slate-950">
              <ShieldCheck size={17} className="text-[#18a058]" />
              <span>Source Coverage</span>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {manifest.source_files.map((source) => (
                <div
                  key={source.relative_path}
                  className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600"
                >
                  <span className="break-all font-mono">{source.relative_path}</span>
                  <span className="shrink-0 text-slate-950">{source.available ? "available" : "missing"}</span>
                </div>
              ))}
            </div>
          </article>

          {manifest.warnings.length ? (
            <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
              <div className="mb-3 text-sm font-black text-amber-950">Warnings</div>
              <ul className="space-y-2 text-sm font-semibold leading-6 text-amber-900">
                {manifest.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </article>
          ) : null}

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Caveats</div>
            <ul className="space-y-2 text-sm font-semibold leading-6 text-slate-700">
              {manifest.caveats.map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          </article>
        </div>
      </section>
    </div>
  );
}
