import { Download, FileArchive, RefreshCw, X } from "lucide-react";
import type { ProjectExportInfo } from "@/lib/types";

type ProjectExportPanelProps = {
  open: boolean;
  info: ProjectExportInfo;
  loading?: boolean;
  actionLoading?: boolean;
  onCreate: () => Promise<void>;
  onRefresh: () => Promise<void>;
  onClose: () => void;
};

export function ProjectExportPanel({
  open,
  info,
  loading = false,
  actionLoading = false,
  onCreate,
  onRefresh,
  onClose
}: ProjectExportPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <FileArchive size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Project Export</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {info.available ? info.relative_path : "No export yet"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="secondary-button" disabled={loading} onClick={onRefresh}>
                <RefreshCw size={16} />
                <span>Refresh</span>
              </button>
              <button className="primary-button" disabled={actionLoading} onClick={onCreate}>
                <Download size={16} />
                <span>Generate zip</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="Close project export">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Latest Zip</div>
            <dl className="grid gap-3 text-xs font-semibold text-slate-600 md:grid-cols-4">
              <div>
                <dt className="text-slate-400">available</dt>
                <dd className="mt-1 text-slate-950">{String(info.available)}</dd>
              </div>
              <div>
                <dt className="text-slate-400">files</dt>
                <dd className="mt-1 text-slate-950">{info.included_file_count ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-400">size_bytes</dt>
                <dd className="mt-1 text-slate-950">{info.size_bytes ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-400">warnings</dt>
                <dd className="mt-1 text-slate-950">{info.warnings.length}</dd>
              </div>
              <div className="md:col-span-4">
                <dt className="text-slate-400">relative_path</dt>
                <dd className="mt-1 break-all font-mono text-slate-950">
                  {info.relative_path ?? info.message ?? "No export has been generated."}
                </dd>
              </div>
            </dl>
          </article>

          <div className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 text-sm font-black text-slate-950">Included Categories</div>
              <dl className="grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                {Object.entries(info.category_counts).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-3 rounded bg-slate-50 px-3 py-2">
                    <dt>{key}</dt>
                    <dd className="font-mono text-slate-950">{value}</dd>
                  </div>
                ))}
              </dl>
            </article>
            <article className="rounded-[8px] border border-slate-200 p-4">
              <div className="mb-3 text-sm font-black text-slate-950">Safety Scope</div>
              <div className="flex flex-wrap gap-2">
                {(info.excluded_patterns ?? []).map((pattern) => (
                  <span key={pattern} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                    {pattern}
                  </span>
                ))}
              </div>
            </article>
          </div>

          {info.warnings.length ? (
            <article className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
              <div className="mb-3 text-sm font-black text-amber-950">Skipped Files</div>
              <div className="grid gap-2 md:grid-cols-2">
                {info.warnings.map((item) => (
                  <div key={`${item.relative_path}:${item.reason}`} className="rounded-[8px] bg-white p-3 text-xs font-semibold text-amber-900 ring-1 ring-amber-200">
                    <div className="font-mono font-black">{item.relative_path}</div>
                    <div className="mt-1">{item.reason}</div>
                  </div>
                ))}
              </div>
            </article>
          ) : null}

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 text-sm font-black text-slate-950">Preview</div>
            <pre className="max-h-[320px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
              {JSON.stringify(
                {
                  export_id: info.export_id,
                  file_name: info.file_name,
                  relative_path: info.relative_path,
                  included_files: info.included_files.slice(0, 24),
                  caveats: info.local_mvp_caveats
                },
                null,
                2
              )}
            </pre>
          </article>
        </div>
      </section>
    </div>
  );
}
