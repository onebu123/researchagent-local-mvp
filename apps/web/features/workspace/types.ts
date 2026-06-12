import type { LucideIcon } from "lucide-react";

export type WorkflowStageStatus = "ready" | "mock" | "needs-review";

export type WorkflowStage = {
  title: string;
  summary: string;
  outputs: string[];
  status: WorkflowStageStatus;
  icon: LucideIcon;
};

export type WorkspaceSignal = {
  label: string;
  value: string;
  tone: "neutral" | "good" | "warn";
};
