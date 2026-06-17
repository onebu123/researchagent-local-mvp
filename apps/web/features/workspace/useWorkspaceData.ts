"use client";

import {
  Archive,
  BookOpenCheck,
  ClipboardCheck,
  FileText,
  FlaskConical
} from "lucide-react";

import type { WorkflowStage, WorkspaceSignal } from "./types";

export function useWorkspaceData(): {
  stages: WorkflowStage[];
  signals: WorkspaceSignal[];
} {
  return {
    signals: [
      { label: "Runtime", value: "Local / Mock-safe", tone: "warn" },
      { label: "Generated code", value: "Approval-gated", tone: "warn" },
      { label: "Version", value: "v3.0.0-rc1", tone: "good" },
      { label: "Trust", value: "Human review required", tone: "good" }
    ],
    stages: [
      {
        title: "Research Brief & Evidence",
        summary: "Define the research question, upload local literature/data, and keep source quality visible before automation.",
        outputs: ["research brief", "local evidence", "workspace status"],
        status: "ready",
        icon: FileText
      },
      {
        title: "Idea Generation",
        summary: "Generate candidate research ideas and experiment plans from project-local evidence and explicit limitations.",
        outputs: ["ideas.json", "experiment_plan.json", "limitations"],
        status: "mock",
        icon: BookOpenCheck
      },
      {
        title: "Sandboxed Experiments",
        summary: "Run registered templates or approval-gated generated-code diagnostics in subprocess or optional Docker sandbox.",
        outputs: ["sandbox outputs", "experiment tree", "code review rounds"],
        status: "needs-review",
        icon: FlaskConical
      },
      {
        title: "Paper Writing & Review",
        summary: "Write Markdown/LaTeX draft papers from experiment outputs, then audit claims and simulated reviewer findings.",
        outputs: ["auto_scientist_paper.md", "reviewer issues", "revision plan"],
        status: "needs-review",
        icon: ClipboardCheck
      },
      {
        title: "Trust Package & Approval",
        summary: "Collect generated code proposals, job logs, human decisions, manuscripts, reviews, and trust package manifests.",
        outputs: ["human review queue", "evidence package", "trust report"],
        status: "ready",
        icon: Archive
      }
    ]
  };
}
