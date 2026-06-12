"use client";

import { Activity, ShieldCheck } from "lucide-react";

import type { WorkspaceSignal } from "./types";

const toneClasses: Record<WorkspaceSignal["tone"], string> = {
  neutral: "border-slate-200 bg-white text-slate-700",
  good: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warn: "border-amber-200 bg-amber-50 text-amber-800"
};

export function CommandCenter({ signals }: { signals: WorkspaceSignal[] }) {
  return (
    <header className="border-b border-slate-200 bg-slate-950 text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 py-10 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-sm text-slate-200">
            <Activity className="h-4 w-4" aria-hidden="true" />
            ResearchAgent Command Center
          </div>
          <h1 className="text-4xl font-semibold tracking-normal text-white sm:text-5xl">
            All-in-one Research Agent Workspace
          </h1>
          <p className="mt-5 text-base leading-7 text-slate-300">
            Literature ingestion, evidence indexing, data analysis, evidence-grounded drafting, claim verification,
            reviewer simulation, revision planning, and exportable audit packages in one auditable workspace.
          </p>
        </div>
        <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:w-[420px]">
          {signals.map((signal) => (
            <div key={signal.label} className={`rounded-lg border px-4 py-3 ${toneClasses[signal.tone]}`}>
              <div className="text-xs font-semibold uppercase tracking-wide opacity-80">{signal.label}</div>
              <div className="mt-1 text-sm font-semibold">{signal.value}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="mx-auto flex w-full max-w-7xl items-center gap-2 px-6 pb-8 text-sm text-slate-300">
        <ShieldCheck className="h-4 w-4 text-emerald-300" aria-hidden="true" />
        Evidence/provenance/audit chain required; demo and mock outputs are not research conclusions.
      </div>
    </header>
  );
}
