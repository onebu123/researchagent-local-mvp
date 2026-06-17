"use client";

import LegacyWorkspace from "./LegacyWorkspace";
import { IterativeAgentLoopPanel } from "@/components/IterativeAgentLoopPanel";

export function AdvancedPanels() {
  return (
    <section className="border-t border-slate-200 bg-slate-100">
      <div className="mx-auto w-full max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Advanced / Diagnostics</p>
          <h2 className="text-2xl font-semibold text-slate-950">Existing research audit panels</h2>
          <p className="max-w-3xl text-sm leading-6 text-slate-600">
            The full legacy workspace remains available below while the command center becomes the primary entry point.
          </p>
        </div>
        <IterativeAgentLoopPanel />
      </div>
      <LegacyWorkspace />
    </section>
  );
}
