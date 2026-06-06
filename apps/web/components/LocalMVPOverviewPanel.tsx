import { FileArchive, FileCheck2, GitBranch, ShieldCheck, TerminalSquare } from "lucide-react";
import type { ProjectDetail, ProjectExportInfo, ReadinessReport, TrustSummary } from "@/lib/types";

type LocalMVPOverviewPanelProps = {
  project: ProjectDetail;
  trustSummary: TrustSummary;
  readinessReport: ReadinessReport;
  projectExport: ProjectExportInfo;
  apiOnline: boolean;
  latestManuscriptVersion: string;
  onOpenTrust: () => void;
  onOpenReadiness: () => void;
  onOpenExport: () => void;
  onRunValidation: () => void;
};

export function LocalMVPOverviewPanel({
  project,
  trustSummary,
  readinessReport,
  projectExport,
  apiOnline,
  latestManuscriptVersion,
  onOpenTrust,
  onOpenReadiness,
  onOpenExport,
  onRunValidation
}: LocalMVPOverviewPanelProps) {
  return (
    <section className="panel p-5" aria-label="Local MVP Overview">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <ShieldCheck size={19} className="text-[#5b6ee1]" />
            <h2 className="text-lg font-black text-slate-950">Local MVP Overview</h2>
          </div>
          <div className="mt-2 grid gap-3 text-sm font-semibold text-slate-600 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-[8px] bg-slate-50 p-3 ring-1 ring-slate-200">
              <div className="text-xs font-bold uppercase text-slate-400">Project Status</div>
              <div className="mt-1 text-slate-950">{project.workflow_status}</div>
              <div className="mt-1 font-mono text-xs">{project.current_step}</div>
            </div>
            <div className="rounded-[8px] bg-slate-50 p-3 ring-1 ring-slate-200">
              <div className="text-xs font-bold uppercase text-slate-400">Global Trust Summary</div>
              <div className="mt-1 text-slate-950">{trustSummary.overall_status}</div>
              <div className="mt-1 font-mono text-xs">{trustSummary.blocking_issues.length} blocking</div>
            </div>
            <div className="rounded-[8px] bg-slate-50 p-3 ring-1 ring-slate-200">
              <div className="text-xs font-bold uppercase text-slate-400">v1.0 readiness</div>
              <div className="mt-1 text-slate-950">{readinessReport.readiness_level}</div>
              <div className="mt-1 font-mono text-xs">{readinessReport.production_gaps.length} gaps</div>
            </div>
            <div className="rounded-[8px] bg-slate-50 p-3 ring-1 ring-slate-200">
              <div className="text-xs font-bold uppercase text-slate-400">Latest Manuscript Version</div>
              <div className="mt-1 truncate font-mono text-slate-950">{latestManuscriptVersion}</div>
              <div className="mt-1 font-mono text-xs">{projectExport.relative_path ?? "no export"}</div>
            </div>
          </div>
        </div>

        <div className="grid min-w-[260px] gap-2">
          <button className="secondary-button justify-start" onClick={onOpenTrust}>
            <ShieldCheck size={16} />
            <span>Open trust dashboard</span>
          </button>
          <button className="secondary-button justify-start" onClick={onOpenReadiness}>
            <FileCheck2 size={16} />
            <span>Open release panel</span>
          </button>
          <button className="secondary-button justify-start" onClick={onOpenExport}>
            <FileArchive size={16} />
            <span>Open export panel</span>
          </button>
          <button className="primary-button justify-start" onClick={onRunValidation}>
            <TerminalSquare size={16} />
            <span>Run validation</span>
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-xs font-bold text-slate-600">
        <span className="rounded-full bg-slate-100 px-2 py-1 ring-1 ring-slate-200">
          API {apiOnline ? "online" : "mock data"}
        </span>
        <span className="rounded-full bg-slate-100 px-2 py-1 ring-1 ring-slate-200">
          <GitBranch className="mr-1 inline" size={12} />
          Local MVP release candidate
        </span>
      </div>
    </section>
  );
}
