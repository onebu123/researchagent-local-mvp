import { CheckCircle2, Container, Database, KeyRound, ListChecks, ShieldAlert } from "lucide-react";
import type { ProductionScaffoldReport } from "@/lib/types";

type ProductionScaffoldPanelProps = {
  report: ProductionScaffoldReport;
  apiOnline: boolean;
};

const capabilityIcons = {
  database: Database,
  task_queue: ListChecks,
  auth: KeyRound,
  containers: Container
};

function capabilityTone(configured: boolean) {
  return configured ? "text-[#157347]" : "text-[#b7791f]";
}

export function ProductionScaffoldPanel({ report, apiOnline }: ProductionScaffoldPanelProps) {
  return (
    <section className="panel p-5" aria-label="v2.0 Research Workspace scaffold">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Container size={19} className="text-[#5b6ee1]" />
            <h2 className="text-lg font-black text-slate-950">Research Workspace Scaffold</h2>
          </div>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-slate-500">
            v2.0 adds optional PostgreSQL, worker, auth, Docker, and deployment scaffolding while
            keeping the local demo on mock fallback.
          </p>
        </div>
        <div className="rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-black text-slate-700">
          {apiOnline ? report.status : "mock scaffold fallback"}
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {report.capabilities.map((capability) => {
          const Icon =
            capabilityIcons[capability.name as keyof typeof capabilityIcons] ?? CheckCircle2;
          return (
            <div key={capability.name} className="rounded-[8px] bg-slate-50 p-3 ring-1 ring-slate-200">
              <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-400">
                <Icon size={15} className={capabilityTone(capability.configured)} />
                <span data-testid={`v2-capability-${capability.name}`}>
                  {capability.name.replace("_", " ")}
                </span>
              </div>
              <div className="mt-2 text-sm font-black text-slate-950">{capability.mode}</div>
              <div className="mt-1 font-mono text-xs text-slate-500">
                fallback: {capability.fallback}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-[8px] border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-black text-slate-900">
            <ShieldAlert size={16} className="text-[#b7791f]" />
            <span>Deployment Blockers</span>
          </div>
          <ul className="space-y-2 text-sm font-semibold leading-5 text-slate-600">
            {report.blocking_items.slice(0, 4).map((item) => (
              <li key={item} className="flex gap-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#b7791f]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-[8px] border border-slate-200 bg-white p-3">
          <div className="text-xs font-black uppercase text-slate-400">Validation</div>
          <div className="mt-2 font-mono text-sm font-black text-slate-950">
            {report.validation.script}
          </div>
          <div className="mt-3 grid gap-2 text-xs font-bold text-slate-600">
            <span>API key required: {report.validation.requires_api_key ? "yes" : "no"}</span>
            <span>
              External network required: {report.validation.requires_external_network ? "yes" : "no"}
            </span>
            <span>Worker: {report.worker.entrypoint}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
