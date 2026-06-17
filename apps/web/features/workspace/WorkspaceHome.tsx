"use client";

import { CommandCenter } from "./CommandCenter";
import { AdvancedPanels } from "./AdvancedPanels";
import { AutoScientistWorkbench } from "@/components/AutoScientistWorkbench";
import { WorkflowStepper } from "./WorkflowStepper";
import { useWorkspaceData } from "./useWorkspaceData";

export function WorkspaceHome() {
  const { stages, signals } = useWorkspaceData();
  return (
    <main className="min-h-screen bg-slate-50">
      <CommandCenter signals={signals} />
      <AutoScientistWorkbench />
      <WorkflowStepper stages={stages} />
      <AdvancedPanels />
    </main>
  );
}
