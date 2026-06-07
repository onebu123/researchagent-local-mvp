import {
  BarChart3,
  CheckCircle2,
  Download,
  FileText,
  SearchCheck,
  ShieldCheck,
  TriangleAlert
} from "lucide-react";
import type {
  ProjectDetail,
  ProjectExportInfo,
  ReadinessReport,
  TrustSummary,
  WorkspaceExportManifest
} from "@/lib/types";

type UXConsolidationPanelProps = {
  project: ProjectDetail;
  apiOnline: boolean;
  running: boolean;
  trustSummary: TrustSummary;
  readinessReport: ReadinessReport;
  projectExport: ProjectExportInfo;
  workspaceExport: WorkspaceExportManifest;
  onOpenTrust: () => void;
  onOpenRAGQuality: () => void;
  onOpenStatisticalAssistant: () => void;
  onOpenWorkspaceExport: () => void;
};

function statusTone(value: boolean) {
  return value ? "text-[#157347]" : "text-[#b7791f]";
}

export function UXConsolidationPanel({
  project,
  apiOnline,
  running,
  trustSummary,
  readinessReport,
  projectExport,
  workspaceExport,
  onOpenTrust,
  onOpenRAGQuality,
  onOpenStatisticalAssistant,
  onOpenWorkspaceExport
}: UXConsolidationPanelProps) {
  const workflowReady = project.workflow_status === "completed" && !running;
  const exportReady = Boolean(projectExport.available || workspaceExport.available);
  const trustStatus = trustSummary.overall_status ?? "needs_review";
  const readinessLevel = readinessReport.readiness_level ?? "local_review_required";
  const mockFallbackLabel = "Mock fallback active";
  const connectionLabel = apiOnline ? "FastAPI connected" : "Fallback mode active";

  const signals = [
    {
      label: "Runtime",
      value: connectionLabel,
      icon: apiOnline ? CheckCircle2 : TriangleAlert,
      tone: statusTone(apiOnline),
      note: apiOnline ? "Live local API data" : "Demo remains usable without API or network"
    },
    {
      label: "Workflow",
      value: workflowReady ? "Demo workflow complete" : "Review current workflow state",
      icon: CheckCircle2,
      tone: statusTone(workflowReady),
      note: `Current step: ${project.current_step}`
    },
    {
      label: "Trust",
      value: trustStatus,
      icon: ShieldCheck,
      tone: "text-[#4052c6]",
      note: readinessLevel
    },
    {
      label: "Exports",
      value: exportReady ? "Local artifacts available" : "Generate export when needed",
      icon: Download,
      tone: statusTone(exportReady),
      note: "Project-relative paths only"
    }
  ];

  const actions = [
    {
      label: "Open Global Trust",
      ariaLabel: "Workspace readiness trust summary",
      icon: ShieldCheck,
      onClick: onOpenTrust
    },
    {
      label: "Review RAG Quality",
      ariaLabel: "Workspace readiness retrieval review",
      icon: SearchCheck,
      onClick: onOpenRAGQuality
    },
    {
      label: "Open Statistical Assistant",
      ariaLabel: "Workspace readiness analysis helper",
      icon: BarChart3,
      onClick: onOpenStatisticalAssistant
    },
    {
      label: "Open Workspace Export",
      ariaLabel: "Workspace readiness export handoff",
      icon: FileText,
      onClick: onOpenWorkspaceExport
    }
  ];

  return (
    <section
      className="panel overflow-hidden"
      aria-label="v1.6 UX workspace status"
      data-fallback-label={mockFallbackLabel}
      data-testid="ux-consolidation-panel"
    >
      <div className="border-b border-slate-200 px-5 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-xs font-black uppercase text-slate-400">Research Workspace</div>
            <h2 className="text-xl font-black text-slate-950">Workspace Readiness</h2>
            <p className="mt-1 max-w-2xl text-sm font-semibold leading-6 text-slate-500">
              Local demo controls stay visible in mock mode; trust, retrieval, analysis, and export
              actions remain separate review steps.
            </p>
          </div>
          <div className="rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-black text-slate-700">
            v1.6 UX consolidation
          </div>
        </div>
      </div>

      <div className="grid border-b border-slate-200 md:grid-cols-2 xl:grid-cols-4">
        {signals.map((signal) => {
          const Icon = signal.icon;
          return (
            <div key={signal.label} className="border-t border-slate-100 p-4 md:border-r">
              <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase text-slate-400">
                <Icon size={16} className={signal.tone} />
                <span>{signal.label}</span>
              </div>
              <div className="min-h-[28px] text-sm font-black text-slate-950">{signal.value}</div>
              <div className="mt-1 text-xs font-semibold leading-5 text-slate-500">{signal.note}</div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-2 p-4 sm:grid-cols-2 xl:grid-cols-4">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.label}
              className="secondary-button min-h-[44px] justify-start"
              aria-label={action.ariaLabel}
              onClick={action.onClick}
              data-testid={`ux-action-${action.label.toLowerCase().replaceAll(" ", "-")}`}
            >
              <Icon size={16} />
              <span>{action.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
