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
      { label: "Runtime", value: "Demo Mode / Mock Mode", tone: "warn" },
      { label: "LLM", value: "LLM_MODE=mock by default", tone: "neutral" },
      { label: "Version", value: "v2.0.1-dev", tone: "good" },
      { label: "Trust", value: "Evidence required", tone: "good" }
    ],
    stages: [
      {
        title: "Project Setup",
        summary: "Upload literature, data, figures, and manuscript drafts; inspect project health before running agent steps.",
        outputs: ["project health", "uploaded artifacts", "workspace status"],
        status: "ready",
        icon: FileText
      },
      {
        title: "Knowledge & Evidence Index",
        summary: "Parse PDFs/text, build local literature index, RAG chunks, metadata status, and source passages.",
        outputs: ["PDF parse", "RAG chunks", "source passages"],
        status: "mock",
        icon: BookOpenCheck
      },
      {
        title: "Research & Analysis",
        summary: "Generate topic ideas, profile datasets, run descriptive analysis helpers, and track figure provenance.",
        outputs: ["analysis summary", "statistical assistant", "figure provenance"],
        status: "needs-review",
        icon: FlaskConical
      },
      {
        title: "Manuscript & Review Loop",
        summary: "Draft from allowed evidence, audit claim alignment, ground citations, simulate reviewers, and plan revisions.",
        outputs: ["draft", "reviewer issues", "revision plan"],
        status: "needs-review",
        icon: ClipboardCheck
      },
      {
        title: "Export & Trust Report",
        summary: "Create manuscript exports, audit packages, release readiness checks, and trust dashboards.",
        outputs: ["source package", "evidence package", "trust report"],
        status: "ready",
        icon: Archive
      }
    ]
  };
}
