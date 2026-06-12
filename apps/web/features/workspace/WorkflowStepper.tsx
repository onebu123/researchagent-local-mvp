"use client";

import { ChevronRight } from "lucide-react";

import type { WorkflowStage, WorkflowStageStatus } from "./types";

const statusLabels: Record<WorkflowStageStatus, string> = {
  ready: "Ready",
  mock: "Mock Mode",
  "needs-review": "Needs Human Review"
};

const statusClasses: Record<WorkflowStageStatus, string> = {
  ready: "border-emerald-200 bg-emerald-50 text-emerald-800",
  mock: "border-slate-200 bg-slate-100 text-slate-700",
  "needs-review": "border-amber-200 bg-amber-50 text-amber-800"
};

export function WorkflowStepper({ stages }: { stages: WorkflowStage[] }) {
  return (
    <section className="mx-auto w-full max-w-7xl px-6 py-8">
      <div className="grid gap-4 lg:grid-cols-5">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <article
              key={stage.title}
              className="relative min-h-[250px] rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-900 text-white">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusClasses[stage.status]}`}>
                  {statusLabels[stage.status]}
                </span>
              </div>
              <h2 className="text-base font-semibold text-slate-950">{stage.title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">{stage.summary}</p>
              <ul className="mt-4 space-y-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                {stage.outputs.map((output) => (
                  <li key={output}>{output}</li>
                ))}
              </ul>
              {index < stages.length - 1 ? (
                <ChevronRight
                  className="absolute -right-3 top-1/2 hidden h-6 w-6 -translate-y-1/2 rounded-full border border-slate-200 bg-white p-1 text-slate-400 lg:block"
                  aria-hidden="true"
                />
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
