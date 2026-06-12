"use client";

import { CommandCenter } from "./CommandCenter";
import { AdvancedPanels } from "./AdvancedPanels";
import { WorkflowStepper } from "./WorkflowStepper";
import { useWorkspaceData } from "./useWorkspaceData";

export function WorkspaceHome() {
  const { stages, signals } = useWorkspaceData();
  return (
    <main className="min-h-screen bg-slate-50">
      <CommandCenter signals={signals} />
      <WorkflowStepper stages={stages} />
      <AdvancedPanels />
    </main>
  );
}
