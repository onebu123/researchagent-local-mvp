"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  Beaker,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  FlaskConical,
  GitBranch,
  RefreshCw,
  ShieldCheck,
  TerminalSquare,
  XCircle
} from "lucide-react";

import {
  approveAutoScientistGeneratedCode,
  applyAutoScientistTreeRevision,
  cancelProjectJob,
  createAutoScientistIdeas,
  createAutoScientistExperimentClaimBindings,
  createAutoScientistPaperCitationBindings,
  compileAutoScientistPaper,
  createAutoScientistTreeRevisionPlan,
  getAutoScientistExperimentTree,
  getAutoScientistExperimentClaimBindings,
  getAutoScientistPaperCitationBindings,
  getAutoScientistPaperCompileReport,
  getAutoScientistGeneratedCodeApprovals,
  getAutoScientistGeneratedCodeProposals,
  getAutoScientistStatus,
  getAutoScientistTreeRevisionPlan,
  getHumanReviewQueue,
  getLiterature,
  getProjectJobEvents,
  getProjectJobLog,
  getProjectJobs,
  listProjects,
  rerunAutoScientistExperimentTreeNode,
  rerunAutoScientistGeneratedCode,
  rewriteAutoScientistPaperFromTree,
  selectAutoScientistExperimentTreeNode,
  startAutoScientistJob
} from "@/lib/api";
import type {
  AutoScientistExperimentTree,
  AutoScientistExperimentClaimBindings,
  AutoScientistPaperCitationBindings,
  AutoScientistPaperCompileReport,
  AutoScientistGeneratedCodeApproval,
  AutoScientistGeneratedCodeProposal,
  AutoScientistIdeas,
  AutoScientistStatus,
  AutoScientistTreeRevisionPlan,
  HumanReviewQueue,
  LiteratureRecord,
  ProjectJob,
  ProjectJobEvents,
  ProjectJobLog,
  ProjectRead
} from "@/lib/types";

type SourceMode = "deterministic" | "mock_llm" | "live_llm";
type SandboxMode = "subprocess" | "docker";
type Strategy = "lexical_diagnostics" | "retrieval_ablation" | "claim_support_matrix" | "descriptive_table_profile";
type TabKey = "ideas" | "experiments" | "code" | "paper" | "trust";

type WorkbenchSnapshot = {
  status: AutoScientistStatus | null;
  jobs: ProjectJob[];
  jobLog: ProjectJobLog | null;
  jobEvents: ProjectJobEvents | null;
  proposals: AutoScientistGeneratedCodeProposal[];
  approvals: AutoScientistGeneratedCodeApproval[];
  queue: HumanReviewQueue | null;
  tree: AutoScientistExperimentTree | null;
  treeRevisionPlan: AutoScientistTreeRevisionPlan | null;
  experimentClaimBindings: AutoScientistExperimentClaimBindings | null;
  paperCitationBindings: AutoScientistPaperCitationBindings | null;
  paperCompileReport: AutoScientistPaperCompileReport | null;
};

const strategyLabels: Record<Strategy, string> = {
  lexical_diagnostics: "Lexical diagnostics",
  retrieval_ablation: "Retrieval ablation",
  claim_support_matrix: "Claim support matrix",
  descriptive_table_profile: "Descriptive table profile"
};

const tabs: Array<{ key: TabKey; label: string; description: string }> = [
  { key: "ideas", label: "Ideas", description: "Brief, hypotheses, and idea generation" },
  { key: "experiments", label: "Experiments", description: "Sandbox, tree search, jobs, and logs" },
  { key: "code", label: "Code Review", description: "Generated-code proposals and approvals" },
  { key: "paper", label: "Paper", description: "Manuscript and reviewer artifacts" },
  { key: "trust", label: "Trust", description: "Human review queue and export readiness" }
];

const emptySnapshot: WorkbenchSnapshot = {
  status: null,
  jobs: [],
  jobLog: null,
  jobEvents: null,
  proposals: [],
  approvals: [],
  queue: null,
  tree: null,
  treeRevisionPlan: null,
  experimentClaimBindings: null,
  paperCitationBindings: null,
  paperCompileReport: null
};

const mockSnapshot: WorkbenchSnapshot = {
  status: {
    project_id: "demo_project",
    ideas: { idea_count: 3, relative_path: "auto_scientist/ideas.json" },
    experiment_plan: { planned_experiment_count: 5, relative_path: "auto_scientist/experiment_plan.json" },
    analysis: { completed_experiment_count: 4, sandbox_failure_count: 1 },
    review: { overall_decision: "major_revision" },
    latest_run: {
      run_id: "mock_auto_scientist_run",
      status: "demo",
      generated_code_strategy: "retrieval_ablation",
      manuscript_file: "manuscript/auto_scientist_paper.md",
      latex_file: "manuscript/auto_scientist_paper.tex"
    },
    run_count: 1,
    limitations: [
      "Demo Mode / Mock Mode snapshot. It is not a real experiment result.",
      "Generated paper artifacts require human scientific review."
    ],
    generated_code_experiments_enabled: true,
    sandboxed_generated_code: true,
    experiment_tree_search_enabled: true,
    generated_code_revision_loop_enabled: true,
    generated_code_strategy: "retrieval_ablation",
    experiment_tree: { best_node_id: "mock_node_001", node_count: 3 }
  },
  jobs: [
    {
      schema_version: "mock.job.v1",
      project_id: "demo_project",
      job_id: "mock_job_auto_scientist",
      job_type: "auto_scientist_run",
      status: "completed",
      progress: 1,
      current_step: "Demo Auto Scientist workflow completed",
      outputs: ["manuscript/auto_scientist_paper.md"],
      errors: [],
      execution_mode: "background"
    }
  ],
  jobLog: {
    project_id: "demo_project",
    job_id: "mock_job_auto_scientist",
    relative_path: "jobs/mock_job_auto_scientist.log",
    content: "Demo job log: generated ideas, ran sandboxed diagnostics, wrote manuscript draft."
  },
  jobEvents: {
    schema_version: "mock.job.events.v1",
    project_id: "demo_project",
    job_id: "mock_job_auto_scientist",
    events_file: "jobs/mock_job_auto_scientist.events.jsonl",
    latest_sequence: 3,
    returned: 3,
    events: [
      { schema_version: "mock.job.event.v1", sequence: 1, project_id: "demo_project", job_id: "mock_job_auto_scientist", job_type: "auto_scientist_run", event_type: "created", status: "queued", progress: 0, current_step: "queued", message: "Demo job queued", created_at: new Date().toISOString() },
      { schema_version: "mock.job.event.v1", sequence: 2, project_id: "demo_project", job_id: "mock_job_auto_scientist", job_type: "auto_scientist_run", event_type: "progress", status: "running", progress: 0.5, current_step: "running experiments", message: "Demo experiments running", created_at: new Date().toISOString() },
      { schema_version: "mock.job.event.v1", sequence: 3, project_id: "demo_project", job_id: "mock_job_auto_scientist", job_type: "auto_scientist_run", event_type: "terminal", status: "completed", progress: 1, current_step: "completed", message: "Demo job completed", created_at: new Date().toISOString() }
    ]
  },
  proposals: [
    {
      schema_version: "mock.generated_code_proposal.v1",
      project_id: "demo_project",
      run_id: "mock_run",
      experiment_id: "mock_generated_code_exp",
      relative_path: "auto_scientist/generated_code/mock_run/mock_generated_code_exp/code_proposal.json",
      source_file: "auto_scientist/generated_code/mock_run/mock_generated_code_exp/experiment.py",
      input_file: "auto_scientist/generated_code/mock_run/mock_generated_code_exp/input.json",
      source_hash: "mock_source_hash",
      source_mode: "mock_llm",
      generated_code_strategy: "claim_support_matrix",
      human_approval_recommended: true,
      static_scan: { safe: true, findings: [] },
      static_scan_safe: true,
      approval_decision: null,
      source_excerpt: "# Demo generated-code proposal. Review before execution.\n",
      safety_notes: ["Demo proposal only; not a real generated experiment."]
    }
  ],
  approvals: [],
  tree: {
    schema_version: "mock.experiment_tree.v1",
    project_id: "demo_project",
    run_id: "mock_run",
    experiment_tree_file: "auto_scientist/experiment_tree.json",
    node_count: 3,
    edge_count: 2,
    best_node: { node_id: "mock_node_001", experiment_id: "mock_exp_001", template_name: "rag_retrieval_eval", status: "completed", score: 1.72, output_files: ["auto_scientist/experiments/mock/experiment_result.json"] },
    selected_best_node: null,
    selected_best_node_id: null,
    nodes: [
      { node_id: "mock_node_001", experiment_id: "mock_exp_001", template_name: "rag_retrieval_eval", status: "completed", score: 1.72, output_files: ["auto_scientist/experiments/mock/experiment_result.json"] },
      { node_id: "mock_node_002", experiment_id: "mock_exp_002", template_name: "claim_audit_eval", status: "completed", score: 1.21, output_files: ["auto_scientist/experiments/mock/metrics.json"] },
      { node_id: "mock_node_003", experiment_id: "mock_exp_003", template_name: "generated_code_smoke_test", status: "pending_human_approval", score: 0.2, generated_code_execution: true, output_files: ["auto_scientist/generated_code/mock/code_proposal.json"] }
    ],
    edges: [{ from: "mock_node_001", to: "mock_node_002" }, { from: "mock_node_001", to: "mock_node_003" }],
    limitations: ["Mock tree nodes are for UI preview only."]
  },
  experimentClaimBindings: {
    schema_version: "demo",
    project_id: "demo_project",
    created_at: "demo",
    manuscript_file: "manuscript/auto_scientist_paper.md",
    binding_file: "auto_scientist/experiment_claim_bindings.json",
    binding_markdown_file: "auto_scientist/experiment_claim_bindings.md",
    latest_binding_file: "auto_scientist/latest_experiment_claim_binding.json",
    experiment_record_count: 3,
    summary: { total_sentences_checked: 6, bound: 3, weakly_bound: 2, unbound: 1, human_review_required: 3 },
    bindings: [],
    limitations: ["Demo binding snapshot; not scientific proof."]
  },
  treeRevisionPlan: {
    schema_version: "mock.tree_revision_plan.v1",
    project_id: "demo_project",
    selected_node_id: "mock_node_001",
    selected_node: { node_id: "mock_node_001", template_name: "rag_retrieval_eval", status: "completed", score: 1.72 },
    critiques: [
      { critique_id: "mock_tree_critique", severity: "warning", title: "Tree result needs human review", recommended_action: "add_cautious_tree_interpretation" }
    ],
    patch_suggestions: [
      { patch_id: "tree_revision_patch_001", review_id: "auto_scientist_tree_revision_patch_tree_revision_patch_001", risk_level: "medium", reason: "Add cautious selected-node interpretation.", requires_human_approval: true, status: "pending_human_approval" }
    ],
    human_approval_required: true,
    limitations: ["Mock revision plan only."]
  },
  paperCitationBindings: {
    schema_version: "mock.paper_citation_binding.v1",
    project_id: "demo_project",
    generated_at: new Date().toISOString(),
    manuscript_file: "manuscript/auto_scientist_paper.md",
    binding_file: "manuscript/paper_citation_bindings.json",
    binding_markdown_file: "manuscript/paper_citation_bindings.md",
    citation_bound_draft_file: "manuscript/auto_scientist_paper_citation_bound.md",
    retrieval_mode: "local_hybrid_fts",
    top_k: 3,
    formal_reference_count: 0,
    summary: { claim_like_sentences: 4, bound: 1, weak_binding: 2, unbound: 1, source_passage_only: 3, human_review_required: 3 },
    bindings: [],
    limitations: ["Demo citation bindings; not citation verification."]
  },
  paperCompileReport: {
    schema_version: "mock.paper_compile.v1",
    project_id: "demo_project",
    created_at: new Date().toISOString(),
    relative_path: "manuscript/latex_compile_report.json",
    markdown_report_file: "manuscript/latex_compile_report.md",
    source_tex_file: "manuscript/auto_scientist_paper.tex",
    engine_requested: "auto",
    engine_used: null,
    compile_status: "tool_unavailable",
    compiled_pdf: false,
    pdf_file: null,
    preview_pdf_generated: true,
    preview_pdf_file: "manuscript/auto_scientist_paper_preview.pdf",
    stdout_file: null,
    stderr_file: null,
    latex_safety_findings: [],
    warnings: ["Demo preview only."],
    limitations: ["Demo compile report; not publication readiness."]
  },
  queue: {
    project_id: "demo_project",
    generated_at: new Date().toISOString(),
    relative_path: "trust/human_review_queue.json",
    items: [
      {
        review_id: "mock_code_approval",
        review_type: "auto_scientist",
        severity: "blocking",
        title: "Generated experiment code requires approval",
        description: "Review source hash, static scan, and sandbox policy before running generated code.",
        artifact_path: "auto_scientist/generated_code/mock_run/mock_generated_code_exp/code_proposal.json",
        entity_type: "auto_scientist_generated_code",
        entity_id: "mock_generated_code_exp",
        recommended_action: "approve_or_reject_generated_code",
        status: "pending",
        created_at: new Date().toISOString(),
        decided_at: null,
        decision_reason: "",
        human_review_required: true
      }
    ],
    summary: { total: 1, pending: 1, blocking: 1 },
    limitations: ["Mock review queue for offline UI rendering."]
  }
};

function asCount(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "string" && value.trim()) return value;
  return "—";
}

function getRecordNumber(record: Record<string, unknown> | undefined, key: string): number | null {
  const value = record?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function getRecordString(record: Record<string, unknown> | undefined, key: string): string | null {
  const value = record?.[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function latestJob(jobs: ProjectJob[]): ProjectJob | null {
  return jobs[0] ?? null;
}

function isActiveJob(job: ProjectJob | null): boolean {
  return Boolean(job && ["queued", "running", "cancelling"].includes(String(job.status)));
}

function pendingProposals(proposals: AutoScientistGeneratedCodeProposal[]): AutoScientistGeneratedCodeProposal[] {
  return proposals.filter((proposal) => !proposal.approval_decision && proposal.human_approval_recommended);
}

function statusBadge(status: string | undefined): string {
  const normalized = (status || "unknown").toLowerCase();
  if (normalized === "completed" || normalized === "approved") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (normalized === "failed" || normalized === "rejected" || normalized === "blocking" || normalized === "cancelled") return "border-rose-200 bg-rose-50 text-rose-800";
  if (normalized === "running" || normalized === "queued") return "border-blue-200 bg-blue-50 text-blue-800";
  return "border-amber-200 bg-amber-50 text-amber-800";
}

function MiniStat({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "good" | "warn" }) {
  const classes = {
    neutral: "border-slate-200 bg-white text-slate-700",
    good: "border-emerald-200 bg-emerald-50 text-emerald-800",
    warn: "border-amber-200 bg-amber-50 text-amber-800"
  }[tone];
  return (
    <div className={`rounded-lg border px-4 py-3 ${classes}`}>
      <div className="text-xs font-bold uppercase tracking-wide opacity-75">{label}</div>
      <div className="mt-1 text-lg font-black">{value}</div>
    </div>
  );
}

function OverviewCard({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-white">{icon}</div>
        <h3 className="text-sm font-black text-slate-950">{title}</h3>
      </div>
      <p className="text-xs leading-5 text-slate-600">{body}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-lg font-black text-slate-950">{title}</h3>
      {children}
    </section>
  );
}

function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="text-sm font-bold text-slate-700">{children}</span>;
}

export function AutoScientistWorkbench() {
  const [projects, setProjects] = useState<ProjectRead[]>([]);
  const [projectId, setProjectId] = useState("demo_project");
  const [topic, setTopic] = useState("evidence-grounded autonomous research workflow");
  const [researchQuestion, setResearchQuestion] = useState(
    "Can local evidence support an automatically generated research manuscript without unsafe claims?"
  );
  const [sourceMode, setSourceMode] = useState<SourceMode>("deterministic");
  const [sandboxMode, setSandboxMode] = useState<SandboxMode>("subprocess");
  const [strategy, setStrategy] = useState<Strategy>("retrieval_ablation");
  const [allowGeneratedCode, setAllowGeneratedCode] = useState(true);
  const [requiresApproval, setRequiresApproval] = useState(true);
  const [enableTree, setEnableTree] = useState(true);
  const [enableRevision, setEnableRevision] = useState(true);
  const [dockerImage, setDockerImage] = useState("python:3.11-slim");
  const [snapshot, setSnapshot] = useState<WorkbenchSnapshot>(emptySnapshot);
  const [ideas, setIdeas] = useState<AutoScientistIdeas | null>(null);
  const [literatureRecords, setLiteratureRecords] = useState<LiteratureRecord[]>([]);
  const [selectedReferenceIds, setSelectedReferenceIds] = useState<string[]>([]);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState("Ready to run local Auto Scientist workflow.");
  const [apiMode, setApiMode] = useState<"live" | "mock">("live");
  const [approvalReason, setApprovalReason] = useState("Reviewed static scan, source hash, and sandbox policy.");
  const [activeTab, setActiveTab] = useState<TabKey>("ideas");

  const currentJob = useMemo(() => latestJob(snapshot.jobs), [snapshot.jobs]);
  const proposalsPending = useMemo(() => pendingProposals(snapshot.proposals), [snapshot.proposals]);
  const reviewSummary = snapshot.queue?.summary ?? {};
  const status = snapshot.status;
  const analysis = status?.analysis;
  const latestRun = status?.latest_run;
  const revisionPlan = snapshot.treeRevisionPlan;
  const experimentBindings = snapshot.experimentClaimBindings;
  const citationBindings = snapshot.paperCitationBindings;
  const compileReport = snapshot.paperCompileReport;

  async function refresh(targetProjectId = projectId, silent = false) {
    if (!targetProjectId.trim()) return;
    if (!silent) setBusyAction((current) => current ?? "refresh");
    try {
      const [statusResult, jobsResult, proposalsResult, approvalsResult, queueResult, treeResult, treeRevisionResult, bindingResult, citationBindingResult, compileResult, literatureResult] = await Promise.allSettled([
        getAutoScientistStatus(targetProjectId),
        getProjectJobs(targetProjectId, 5),
        getAutoScientistGeneratedCodeProposals(targetProjectId),
        getAutoScientistGeneratedCodeApprovals(targetProjectId),
        getHumanReviewQueue(targetProjectId),
        getAutoScientistExperimentTree(targetProjectId),
        getAutoScientistTreeRevisionPlan(targetProjectId),
        getAutoScientistExperimentClaimBindings(targetProjectId),
        getAutoScientistPaperCitationBindings(targetProjectId),
        getAutoScientistPaperCompileReport(targetProjectId),
        getLiterature(targetProjectId)
      ]);
      const jobs = jobsResult.status === "fulfilled" ? jobsResult.value : [];
      let jobLog: ProjectJobLog | null = null;
      let jobEvents: ProjectJobEvents | null = null;
      if (jobs[0]) {
        const [logResult, eventsResult] = await Promise.all([
          Promise.resolve(getProjectJobLog(targetProjectId, jobs[0].job_id)).then(
            (value) => ({ status: "fulfilled" as const, value }),
            () => ({ status: "rejected" as const })
          ),
          Promise.resolve(getProjectJobEvents(targetProjectId, jobs[0].job_id)).then(
            (value) => ({ status: "fulfilled" as const, value }),
            () => ({ status: "rejected" as const })
          )
        ]);
        if (logResult.status === "fulfilled") jobLog = logResult.value;
        if (eventsResult.status === "fulfilled") jobEvents = eventsResult.value;
      }
      setSnapshot({
        status: statusResult.status === "fulfilled" ? statusResult.value : null,
        jobs,
        jobLog,
        jobEvents,
        proposals: proposalsResult.status === "fulfilled" ? proposalsResult.value : [],
        approvals: approvalsResult.status === "fulfilled" ? approvalsResult.value : [],
        queue: queueResult.status === "fulfilled" ? queueResult.value : null,
        tree: treeResult.status === "fulfilled" ? treeResult.value : null,
        treeRevisionPlan: treeRevisionResult.status === "fulfilled" ? treeRevisionResult.value : null,
        experimentClaimBindings: bindingResult.status === "fulfilled" ? bindingResult.value : null,
        paperCitationBindings: citationBindingResult.status === "fulfilled" ? citationBindingResult.value : null,
        paperCompileReport: compileResult.status === "fulfilled" ? compileResult.value : null
      });
      const records = literatureResult.status === "fulfilled" ? literatureResult.value : [];
      setLiteratureRecords(records);
      setSelectedReferenceIds((current) => current.filter((id) => records.some((record) => record.literature_id === id)));
      setApiMode("live");
      if (!silent) setMessage("Workspace status refreshed from local backend.");
    } catch (error) {
      setSnapshot(mockSnapshot);
      setLiteratureRecords([]);
      setSelectedReferenceIds([]);
      setApiMode("mock");
      setMessage(error instanceof Error ? `Backend unavailable; showing Demo Mode / Mock Mode. ${error.message}` : "Backend unavailable; showing Demo Mode / Mock Mode.");
    } finally {
      if (!silent) setBusyAction(null);
    }
  }

  useEffect(() => {
    let active = true;
    async function loadProjects() {
      try {
        const value = await listProjects();
        if (!active) return;
        setProjects(value);
        if (value[0]?.id) {
          setProjectId(value[0].id);
          await refresh(value[0].id);
        } else {
          await refresh("demo_project");
        }
      } catch {
        if (!active) return;
        setSnapshot(mockSnapshot);
        setApiMode("mock");
        setMessage("Backend unavailable; showing Demo Mode / Mock Mode Auto Scientist preview.");
      }
    }
    void loadProjects();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isActiveJob(currentJob) || apiMode !== "live") return;
    const interval = window.setInterval(() => {
      void refresh(projectId, true);
    }, 2500);
    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiMode, projectId, currentJob?.job_id, currentJob?.status]);

  function runPayload(forceProposalGate = false) {
    return {
      topic,
      research_question: researchQuestion,
      max_ideas: 2,
      max_experiments_per_idea: 2,
      paper_type: "research_article",
      retrieval_mode: "local_hybrid_fts",
      write_paper: true,
      export_latex: true,
      allow_generated_code_experiments: allowGeneratedCode,
      generated_code_sandbox_mode: sandboxMode,
      generated_code_docker_image: sandboxMode === "docker" ? dockerImage : undefined,
      generated_code_source_mode: forceProposalGate ? "mock_llm" : sourceMode,
      generated_code_strategy: strategy,
      generated_code_requires_approval: forceProposalGate ? true : requiresApproval,
      generated_code_approved: false,
      enable_generated_code_revision_loop: enableRevision,
      generated_code_revision_rounds: enableRevision ? 1 : 0,
      enable_experiment_tree_search: enableTree,
      experiment_tree_max_depth: enableTree ? 1 : 0,
      experiment_tree_branching_factor: 2,
      reference_literature_ids: selectedReferenceIds
    } as const;
  }

  async function generateIdeas() {
    setBusyAction("ideas");
    try {
      const value = await createAutoScientistIdeas(projectId, {
        topic,
        research_question: researchQuestion,
        max_ideas: 3,
        reference_literature_ids: selectedReferenceIds
      });
      setIdeas(value);
      setApiMode("live");
      setMessage("Generated local research ideas. These are draft hypotheses, not scientific conclusions.");
      await refresh(projectId);
    } catch (error) {
      setApiMode("mock");
      setIdeas(mockSnapshot.status?.ideas as AutoScientistIdeas);
      setSnapshot(mockSnapshot);
      setMessage(error instanceof Error ? `Demo fallback after idea generation failed: ${error.message}` : "Demo fallback after idea generation failed.");
    } finally {
      setBusyAction(null);
    }
  }

  async function startJob(forceProposalGate = false) {
    setBusyAction(forceProposalGate ? "proposal-job" : "job");
    try {
      const job = await startAutoScientistJob(projectId, runPayload(forceProposalGate));
      setApiMode("live");
      setActiveTab(forceProposalGate ? "code" : "experiments");
      setMessage(`Started background Auto Scientist job ${job.job_id}. Status will update by polling.`);
      await refresh(projectId);
    } catch (error) {
      setApiMode("mock");
      setSnapshot(mockSnapshot);
      setMessage(error instanceof Error ? `Demo fallback after Auto Scientist job failed: ${error.message}` : "Demo fallback after Auto Scientist job failed.");
    } finally {
      setBusyAction(null);
    }
  }

  async function cancelCurrentJob() {
    if (!currentJob) return;
    setBusyAction("cancel-job");
    try {
      const job = await cancelProjectJob(projectId, currentJob.job_id);
      setApiMode("live");
      setMessage(`Cancellation requested for ${job.job_id}. Local jobs cancel cooperatively at checkpoints.`);
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not cancel job: ${error.message}` : "Could not cancel job.");
    } finally {
      setBusyAction(null);
    }
  }

  async function decideProposal(proposal: AutoScientistGeneratedCodeProposal, decision: "approved" | "rejected") {
    setBusyAction(`${decision}-${proposal.experiment_id}`);
    try {
      await approveAutoScientistGeneratedCode(projectId, {
        run_id: proposal.run_id,
        experiment_id: proposal.experiment_id,
        source_hash: proposal.source_hash,
        decision,
        reason: approvalReason
      });
      setApiMode("live");
      setMessage(`Recorded ${decision} decision for ${proposal.experiment_id}. Rerun Auto Scientist to execute approved source.`);
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not record approval decision: ${error.message}` : "Could not record approval decision.");
    } finally {
      setBusyAction(null);
    }
  }


  async function rerunProposal(proposal: AutoScientistGeneratedCodeProposal) {
    setBusyAction(`rerun-${proposal.experiment_id}`);
    try {
      await rerunAutoScientistGeneratedCode(projectId, {
        run_id: proposal.run_id,
        experiment_id: proposal.experiment_id,
        source_hash: proposal.source_hash,
        sandbox_mode: sandboxMode,
        docker_image: sandboxMode === "docker" ? dockerImage : undefined
      });
      setApiMode("live");
      setMessage(`Reran approved generated-code proposal ${proposal.experiment_id}. Review sandbox artifacts before treating results as evidence.`);
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not rerun proposal: ${error.message}` : "Could not rerun proposal.");
    } finally {
      setBusyAction(null);
    }
  }


  async function selectTreeNode(nodeId: string) {
    setBusyAction(`select-tree-${nodeId}`);
    try {
      await selectAutoScientistExperimentTreeNode(projectId, {
        node_id: nodeId,
        reason: "Selected from Auto Scientist Workbench for manuscript emphasis."
      });
      setApiMode("live");
      setMessage(`Selected experiment tree node ${nodeId}. This is a workflow choice, not scientific proof.`);
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not select tree node: ${error.message}` : "Could not select tree node.");
    } finally {
      setBusyAction(null);
    }
  }

  async function rerunTreeNode(nodeId: string) {
    setBusyAction(`rerun-tree-${nodeId}`);
    try {
      await rerunAutoScientistExperimentTreeNode(projectId, {
        node_id: nodeId,
        sandbox_mode: sandboxMode,
        docker_image: sandboxMode === "docker" ? dockerImage : undefined
      });
      setApiMode("live");
      setMessage(`Reran experiment tree node ${nodeId}. Review rerun outputs before using them in the paper.`);
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not rerun tree node: ${error.message}` : "Could not rerun tree node.");
    } finally {
      setBusyAction(null);
    }
  }

  async function rewritePaperFromTree(nodeId?: string) {
    setBusyAction(nodeId ? `rewrite-tree-${nodeId}` : "rewrite-tree-paper");
    try {
      await rewriteAutoScientistPaperFromTree(projectId, {
        node_id: nodeId,
        reason: nodeId ? "Rewrite manuscript from selected Workbench tree node." : "Rewrite manuscript from current selected or heuristic best tree node."
      });
      setApiMode("live");
      setActiveTab("paper");
      setMessage(nodeId ? `Rewrote Auto Scientist paper using tree node ${nodeId}.` : "Rewrote Auto Scientist paper using current selected/best tree node.");
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not rewrite paper from tree: ${error.message}` : "Could not rewrite paper from tree.");
    } finally {
      setBusyAction(null);
    }
  }

  async function createTreeRevisionPlan(nodeId?: string) {
    setBusyAction(nodeId ? `tree-revision-plan-${nodeId}` : "tree-revision-plan");
    try {
      await createAutoScientistTreeRevisionPlan(projectId, {
        node_id: nodeId,
        reason: nodeId ? "Generate best-node revision plan from selected Workbench tree node." : "Generate best-node revision plan from current selected or heuristic best tree node."
      });
      setApiMode("live");
      setActiveTab("paper");
      setMessage("Generated tree-node-driven critique and manuscript revision patches. Approve patch review items before applying.");
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not generate tree revision plan: ${error.message}` : "Could not generate tree revision plan.");
    } finally {
      setBusyAction(null);
    }
  }


  async function generateExperimentBindings() {
    setBusyAction("experiment-claim-bindings");
    try {
      await createAutoScientistExperimentClaimBindings(projectId, { top_k: 3 });
      setApiMode("live");
      setActiveTab("paper");
      setMessage("Generated experiment-to-manuscript claim bindings. Review weak or unbound sentences before external use.");
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not generate experiment claim bindings: ${error.message}` : "Could not generate experiment claim bindings.");
    } finally {
      setBusyAction(null);
    }
  }


  async function generateCitationBindings() {
    setBusyAction("paper-citation-bindings");
    try {
      await createAutoScientistPaperCitationBindings(projectId, { top_k: 3 });
      setApiMode("live");
      setActiveTab("paper");
      setMessage("Generated paper citation/source-passage bindings. Review source-passage-only or unbound citations before external use.");
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not generate paper citation bindings: ${error.message}` : "Could not generate paper citation bindings.");
    } finally {
      setBusyAction(null);
    }
  }

  async function runPaperCompile() {
    setBusyAction("paper-compile");
    try {
      await compileAutoScientistPaper(projectId, { engine: "auto", generate_preview_pdf: true });
      setApiMode("live");
      setActiveTab("paper");
      setMessage("Ran local LaTeX/PDF pipeline. Review compile report and preview/compiled PDF before external use.");
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not run paper compile pipeline: ${error.message}` : "Could not run paper compile pipeline.");
    } finally {
      setBusyAction(null);
    }
  }

  async function applyTreeRevision() {
    setBusyAction("apply-tree-revision");
    try {
      await applyAutoScientistTreeRevision(projectId, {
        reason: "Apply approved best-node revision patches from Auto Scientist Workbench.",
        require_human_approval: true,
        rerun_claim_audit: true,
        regenerate_trust_package: true
      });
      setApiMode("live");
      setActiveTab("paper");
      setMessage("Applied approved tree revision patches to revised manuscript copy and refreshed audit/trust artifacts.");
      await refresh(projectId);
    } catch (error) {
      setMessage(error instanceof Error ? `Could not apply tree revision patches: ${error.message}` : "Could not apply tree revision patches.");
    } finally {
      setBusyAction(null);
    }
  }

  const completedExperiments = getRecordNumber(analysis, "completed_experiment_count");
  const sandboxFailures = getRecordNumber(analysis, "sandbox_failure_count");
  const runCount = status?.run_count ?? 0;
  const jobProgress = currentJob ? Math.round((currentJob.progress || 0) * 100) : 0;
  const manuscriptFile = getRecordString(latestRun, "manuscript_file") || getRecordString(latestRun, "auto_scientist_paper_file");
  const latexFile = getRecordString(latestRun, "latex_file") || getRecordString(latestRun, "auto_scientist_latex_file");

  return (
    <section className="mx-auto w-full max-w-7xl px-6 pb-10" aria-labelledby="auto-scientist-workbench-title">
      <div className="rounded-2xl border border-slate-200 bg-white/90 shadow-sm">
        <div className="border-b border-slate-200 p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-indigo-800">
                <FlaskConical className="h-4 w-4" aria-hidden="true" />
                AI-Scientist-style workflow
              </div>
              <h2 id="auto-scientist-workbench-title" className="text-3xl font-black tracking-tight text-slate-950">
                Auto Scientist Workbench
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Generate ideas, run local/sandboxed experiments, review generated code proposals, write an auditable
                manuscript, and export trust artifacts. Demo/mock outputs are not scientific conclusions.
              </p>
            </div>
            <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:w-[460px]">
              <MiniStat label="Runtime" value={apiMode === "mock" ? "Demo / Mock" : "Local backend"} tone={apiMode === "mock" ? "warn" : "good"} />
              <MiniStat label="Runs" value={String(runCount)} tone="neutral" />
              <MiniStat label="Job progress" value={currentJob ? `${jobProgress}%` : "—"} tone={isActiveJob(currentJob) ? "warn" : "good"} />
              <MiniStat label="Pending code approvals" value={String(proposalsPending.length)} tone={proposalsPending.length ? "warn" : "good"} />
            </div>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-slate-600">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 font-semibold text-emerald-800">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" /> no automatic scientific proof
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 font-semibold text-amber-800">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" /> generated code requires review
            </span>
            <span className="text-slate-500">{message}</span>
          </div>
        </div>

        <div className="grid gap-4 border-b border-slate-200 bg-slate-50 p-6 md:grid-cols-5">
          <OverviewCard icon={<FileText className="h-4 w-4" aria-hidden="true" />} title="Research Brief & Evidence" body="Define the local research question and evidence scope before automation starts." />
          <OverviewCard icon={<Beaker className="h-4 w-4" aria-hidden="true" />} title="Idea Generation" body="Generate draft hypotheses and experimental directions without treating them as discoveries." />
          <OverviewCard icon={<TerminalSquare className="h-4 w-4" aria-hidden="true" />} title="Sandboxed Experiments" body="Run registered or generated-code diagnostics under local sandbox policies." />
          <OverviewCard icon={<ClipboardCheck className="h-4 w-4" aria-hidden="true" />} title="Paper Writing & Review" body="Write Markdown/LaTeX drafts, then audit claims and reviewer findings." />
          <OverviewCard icon={<GitBranch className="h-4 w-4" aria-hidden="true" />} title="Trust Package & Approval" body="Review pending risks and export auditable project handoff artifacts." />
        </div>

        <div className="border-b border-slate-200 px-6 pt-5">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Auto Scientist workflow tabs">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.key}
                className={`rounded-t-lg border px-4 py-3 text-left text-sm ${
                  activeTab === tab.key
                    ? "border-slate-300 border-b-white bg-white text-slate-950"
                    : "border-transparent bg-slate-100 text-slate-600 hover:bg-white"
                }`}
                onClick={() => setActiveTab(tab.key)}
              >
                <div className="font-black">{tab.label}</div>
                <div className="text-xs opacity-75">{tab.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="p-6">
          {activeTab === "ideas" && (
            <Panel title="Ideas">
              <div className="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
                <div className="space-y-4">
                  <label className="block">
                    <FieldLabel>Project</FieldLabel>
                    <select
                      className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                      value={projectId}
                      onChange={(event) => {
                        setProjectId(event.target.value);
                        void refresh(event.target.value);
                      }}
                    >
                      {projects.length ? projects.map((project) => <option key={project.id} value={project.id}>{project.name} / {project.id}</option>) : <option value="demo_project">demo_project</option>}
                    </select>
                  </label>
                  <label className="block">
                    <FieldLabel>Topic</FieldLabel>
                    <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={topic} onChange={(event) => setTopic(event.target.value)} />
                  </label>
                  <label className="block">
                    <FieldLabel>Research question</FieldLabel>
                    <textarea className="mt-1 min-h-[110px] w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={researchQuestion} onChange={(event) => setResearchQuestion(event.target.value)} />
                  </label>
                  <label className="block">
                    <FieldLabel>Local references</FieldLabel>
                    <select
                      multiple
                      className="mt-1 min-h-[120px] w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                      value={selectedReferenceIds}
                      onChange={(event) => {
                        const values = Array.from(event.currentTarget.selectedOptions)
                          .map((option) => option.value)
                          .slice(0, 10);
                        setSelectedReferenceIds(values);
                      }}
                    >
                      {literatureRecords.length ? literatureRecords.map((record) => (
                        <option key={record.literature_id} value={record.literature_id}>
                          {record.literature_id} / {record.title || record.source_file}
                        </option>
                      )) : <option value="" disabled>No local literature records</option>}
                    </select>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 font-bold text-slate-600">{selectedReferenceIds.length}/10 selected</span>
                      {selectedReferenceIds.map((id) => (
                        <button
                          key={id}
                          type="button"
                          className="rounded-full border border-slate-300 bg-white px-2 py-1 font-bold text-slate-700"
                          onClick={() => setSelectedReferenceIds((current) => current.filter((item) => item !== id))}
                        >
                          {id} x
                        </button>
                      ))}
                    </div>
                  </label>
                  <button
                    type="button"
                    className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
                    disabled={busyAction === "ideas"}
                    onClick={() => void generateIdeas()}
                  >
                    <Beaker className="h-4 w-4" aria-hidden="true" /> Generate ideas
                  </button>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <h4 className="font-black text-slate-950">Idea artifacts</h4>
                  <p className="mt-2 text-sm text-slate-600">Ideas are hypotheses for local experimentation. They are not scientific discoveries until humans verify evidence and methods.</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <MiniStat label="Generated ideas" value={String(ideas?.ideas?.length ?? asCount(status?.ideas?.idea_count))} />
                    <MiniStat label="Plan experiments" value={asCount(status?.experiment_plan?.planned_experiment_count)} />
                    <MiniStat label="Tree nodes" value={asCount(status?.experiment_tree?.node_count)} />
                  </div>
                </div>
              </div>
            </Panel>
          )}

          {activeTab === "experiments" && (
            <Panel title="Sandboxed Experiments">
              <div className="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block">
                      <FieldLabel>Source mode</FieldLabel>
                      <select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={sourceMode} onChange={(event) => setSourceMode(event.target.value as SourceMode)}>
                        <option value="deterministic">deterministic</option>
                        <option value="mock_llm">mock_llm</option>
                        <option value="live_llm">live_llm</option>
                      </select>
                    </label>
                    <label className="block">
                      <FieldLabel>Sandbox</FieldLabel>
                      <select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={sandboxMode} onChange={(event) => setSandboxMode(event.target.value as SandboxMode)}>
                        <option value="subprocess">subprocess</option>
                        <option value="docker">docker</option>
                      </select>
                    </label>
                  </div>
                  <label className="block">
                    <FieldLabel>Experiment code strategy</FieldLabel>
                    <select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={strategy} onChange={(event) => setStrategy(event.target.value as Strategy)}>
                      {Object.entries(strategyLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                  </label>
                  {sandboxMode === "docker" && (
                    <label className="block">
                      <FieldLabel>Docker image allowlist entry</FieldLabel>
                      <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={dockerImage} onChange={(event) => setDockerImage(event.target.value)} />
                    </label>
                  )}
                  <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                    <label className="flex items-center gap-2"><input type="checkbox" checked={allowGeneratedCode} onChange={(event) => setAllowGeneratedCode(event.target.checked)} /> Enable generated-code experiments</label>
                    <label className="flex items-center gap-2"><input type="checkbox" checked={requiresApproval} onChange={(event) => setRequiresApproval(event.target.checked)} /> Require approval gate</label>
                    <label className="flex items-center gap-2"><input type="checkbox" checked={enableTree} onChange={(event) => setEnableTree(event.target.checked)} /> Enable experiment tree search</label>
                    <label className="flex items-center gap-2"><input type="checkbox" checked={enableRevision} onChange={(event) => setEnableRevision(event.target.checked)} /> Enable code diagnostics + revision rerun</label>
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <button type="button" className="inline-flex flex-1 items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={Boolean(busyAction) || isActiveJob(currentJob)} onClick={() => void startJob(false)}>
                      <FlaskConical className="h-4 w-4" aria-hidden="true" /> Run job
                    </button>
                    <button type="button" className="inline-flex flex-1 items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 disabled:opacity-60" disabled={!isActiveJob(currentJob) || busyAction === "cancel-job"} onClick={() => void cancelCurrentJob()}>
                      <XCircle className="h-4 w-4" aria-hidden="true" /> Cancel job
                    </button>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="rounded-lg border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h4 className="font-black text-slate-950">Latest job</h4>
                      <button type="button" className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-bold text-slate-700" onClick={() => void refresh(projectId)}>
                        <RefreshCw className="h-3 w-3" aria-hidden="true" /> Refresh
                      </button>
                    </div>
                    {currentJob ? (
                      <div className="mt-4 space-y-3 text-sm">
                        <div className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${statusBadge(currentJob.status)}`}>{currentJob.status}</div>
                        <div className="h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-indigo-600" style={{ width: `${Math.max(0, Math.min(jobProgress, 100))}%` }} /></div>
                        <p><strong>Job ID:</strong> {currentJob.job_id}</p>
                        <p><strong>Step:</strong> {currentJob.current_step}</p>
                        <p><strong>Execution:</strong> {currentJob.execution_mode || "local"}</p>
                        {currentJob.cancel_requested && <p className="text-amber-700"><strong>Cancellation requested.</strong> Cooperative jobs stop at checkpoint updates.</p>}
                      </div>
                    ) : <p className="mt-3 text-sm text-slate-600">No local Auto Scientist job has been recorded yet.</p>}
                  </div>
                  <div className="rounded-lg border border-slate-200 p-4">
                    <h4 className="font-black text-slate-950">Job event timeline</h4>
                    <div className="mt-3 max-h-64 space-y-2 overflow-auto text-sm">
                      {snapshot.jobEvents?.events?.length ? snapshot.jobEvents.events.map((event) => (
                        <div key={`${event.job_id}-${event.sequence}`} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-bold text-slate-800">#{event.sequence} {event.event_type}</span>
                            <span className={`rounded-full border px-2 py-0.5 text-xs font-bold ${statusBadge(event.status)}`}>{event.status || "event"}</span>
                          </div>
                          <p className="mt-1 text-slate-600">{event.message}</p>
                          <p className="mt-1 text-xs text-slate-500">{event.current_step} · {Math.round((event.progress || 0) * 100)}%</p>
                        </div>
                      )) : <p className="text-slate-600">No job events available yet. New jobs write jobs/&lt;job_id&gt;.events.jsonl and can stream over SSE.</p>}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-4">
                    <h4 className="font-black text-slate-950">Job log</h4>
                    <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">{snapshot.jobLog?.content || "No job log available yet."}</pre>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h4 className="font-black text-slate-950">Experiment tree nodes</h4>
                      <button type="button" className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-bold text-slate-700 disabled:opacity-60" disabled={!snapshot.tree?.nodes?.length || Boolean(busyAction)} onClick={() => void rewritePaperFromTree()}>
                        <FileText className="h-3 w-3" aria-hidden="true" /> Rewrite paper from best
                      </button>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">Tree scores are local workflow heuristics, not scientific validity metrics. Select/rerun nodes before using them in a manuscript.</p>
                    <div className="mt-3 max-h-80 space-y-3 overflow-auto text-sm">
                      {snapshot.tree?.nodes?.length ? snapshot.tree.nodes.map((node) => (
                        <article key={node.node_id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <h5 className="font-black text-slate-950">{node.node_id}</h5>
                              <p className="mt-1 text-xs text-slate-500">{node.template_name || "unknown template"} · score {typeof node.score === "number" ? node.score.toFixed(3) : "—"}</p>
                            </div>
                            <span className={`rounded-full border px-2 py-0.5 text-xs font-bold ${statusBadge(node.status)}`}>{node.status || "node"}</span>
                          </div>
                          <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
                            <span>Depth: {node.depth ?? "—"}</span>
                            <span>Claims: {node.claim_count ?? "—"}</span>
                            <span>{node.generated_code_execution ? "Generated code" : "Registered template"}</span>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <button type="button" className="rounded-md bg-slate-950 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-60" disabled={busyAction === `select-tree-${node.node_id}`} onClick={() => void selectTreeNode(node.node_id)}>Select best</button>
                            <button type="button" className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-bold text-slate-700 disabled:opacity-60" disabled={busyAction === `rerun-tree-${node.node_id}`} onClick={() => void rerunTreeNode(node.node_id)}>Rerun node</button>
                            <button type="button" className="rounded-md border border-indigo-300 px-3 py-1.5 text-xs font-bold text-indigo-700 disabled:opacity-60" disabled={busyAction === `rewrite-tree-${node.node_id}`} onClick={() => void rewritePaperFromTree(node.node_id)}>Rewrite paper</button>
                          </div>
                        </article>
                      )) : <p className="text-slate-600">No experiment tree nodes available yet. Enable experiment tree search and run an Auto Scientist job.</p>}
                    </div>
                  </div>
                </div>
              </div>
            </Panel>
          )}

          {activeTab === "code" && (
            <Panel title="Code Review">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <button type="button" className="inline-flex items-center gap-2 rounded-md bg-amber-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={Boolean(busyAction) || isActiveJob(currentJob)} onClick={() => void startJob(true)}>
                  <TerminalSquare className="h-4 w-4" aria-hidden="true" /> Create approval-gated proposal
                </button>
                <label className="min-w-[280px] flex-1 text-sm font-bold text-slate-700">
                  Approval reason
                  <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={approvalReason} onChange={(event) => setApprovalReason(event.target.value)} />
                </label>
              </div>
              <div className="space-y-4">
                {snapshot.proposals.length ? snapshot.proposals.map((proposal) => (
                  <article key={`${proposal.run_id}-${proposal.experiment_id}-${proposal.source_hash}`} className="rounded-lg border border-slate-200 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h4 className="font-black text-slate-950">{proposal.experiment_id}</h4>
                        <p className="mt-1 text-xs text-slate-500">{proposal.relative_path}</p>
                      </div>
                      <span className={`rounded-full border px-3 py-1 text-xs font-bold ${statusBadge(proposal.approval_decision || (proposal.static_scan_safe ? "approved" : "blocking"))}`}>
                        {proposal.approval_decision || (proposal.static_scan_safe ? "scan safe" : "scan blocked")}
                      </span>
                    </div>
                    <div className="mt-3 grid gap-3 text-sm md:grid-cols-3">
                      <p><strong>Source mode:</strong> {proposal.source_mode || "unknown"}</p>
                      <p><strong>Strategy:</strong> {proposal.generated_code_strategy || "unknown"}</p>
                      <p><strong>Source hash:</strong> <code className="text-xs">{proposal.source_hash.slice(0, 16)}…</code></p>
                    </div>
                    <pre className="mt-3 max-h-52 overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">{proposal.source_excerpt || "No source excerpt available."}</pre>
                    {proposal.safety_notes?.length ? <ul className="mt-3 list-disc pl-5 text-sm text-amber-700">{proposal.safety_notes.map((note) => <li key={note}>{note}</li>)}</ul> : null}
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button type="button" className="inline-flex items-center gap-2 rounded-md bg-emerald-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-60" disabled={Boolean(proposal.approval_decision) || busyAction === `approved-${proposal.experiment_id}`} onClick={() => void decideProposal(proposal, "approved")}>
                        <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Approve
                      </button>
                      <button type="button" className="inline-flex items-center gap-2 rounded-md bg-rose-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-60" disabled={Boolean(proposal.approval_decision) || busyAction === `rejected-${proposal.experiment_id}`} onClick={() => void decideProposal(proposal, "rejected")}>
                        <XCircle className="h-4 w-4" aria-hidden="true" /> Reject
                      </button>
                      <button type="button" className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700 disabled:opacity-60" disabled={proposal.approval_decision !== "approved" || busyAction === `rerun-${proposal.experiment_id}`} onClick={() => void rerunProposal(proposal)}>
                        <RefreshCw className="h-4 w-4" aria-hidden="true" /> Rerun approved proposal
                      </button>
                    </div>
                  </article>
                )) : <p className="rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-600">No generated-code proposals yet. Create an approval-gated proposal to review source hash, static scan, and sandbox policy before execution.</p>}
              </div>
            </Panel>
          )}

          {activeTab === "paper" && (
            <Panel title="Paper Writing & Review">
              <div className="mb-4 rounded-lg border border-indigo-100 bg-indigo-50 p-4 text-sm text-indigo-900">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <strong>Selected experiment tree node:</strong> {snapshot.tree?.selected_best_node_id || snapshot.tree?.best_node?.node_id || "none yet"}
                    <p className="mt-1 text-xs text-indigo-800">Paper rewrites can emphasize the selected/best node, but the manuscript remains an AI-generated draft requiring human review.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" className="rounded-md bg-indigo-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-60" disabled={!snapshot.tree?.nodes?.length || busyAction === "rewrite-tree-paper"} onClick={() => void rewritePaperFromTree()}>Rewrite from selected/best node</button>
                    <button type="button" className="rounded-md bg-slate-950 px-3 py-2 text-xs font-bold text-white disabled:opacity-60" disabled={!snapshot.tree?.nodes?.length || busyAction === "tree-revision-plan"} onClick={() => void createTreeRevisionPlan()}>Generate revision plan</button>
                    <button type="button" className="rounded-md border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700 disabled:opacity-60" disabled={!revisionPlan?.patch_suggestions?.length || busyAction === "apply-tree-revision"} onClick={() => void applyTreeRevision()}>Apply approved patches</button>
                    <button type="button" className="rounded-md border border-emerald-300 px-3 py-2 text-xs font-bold text-emerald-700 disabled:opacity-60" disabled={busyAction === "experiment-claim-bindings"} onClick={() => void generateExperimentBindings()}>Bind claims to experiments</button>
                    <button type="button" className="rounded-md border border-sky-300 px-3 py-2 text-xs font-bold text-sky-700 disabled:opacity-60" disabled={busyAction === "paper-citation-bindings"} onClick={() => void generateCitationBindings()}>Bind citations</button>
                    <button type="button" className="rounded-md border border-purple-300 px-3 py-2 text-xs font-bold text-purple-700 disabled:opacity-60" disabled={busyAction === "paper-compile"} onClick={() => void runPaperCompile()}>Compile / preview PDF</button>
                  </div>
                </div>
              </div>
              {revisionPlan && (
                <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <strong>Best-node revision plan:</strong> {revisionPlan.patch_suggestions?.length || 0} patch suggestion(s), {revisionPlan.critiques?.length || 0} critique(s).
                      <p className="mt-1 text-xs text-amber-800">Patch suggestions require human approval through the Human Review Queue before application. Applying patches writes a revised copy, not the source paper.</p>
                    </div>
                    <span className="rounded-full border border-amber-300 bg-white px-3 py-1 text-xs font-bold">{revisionPlan.selected_node_id || "selected/best node"}</span>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {revisionPlan.patch_suggestions?.slice(0, 4).map((patch) => (
                      <div key={patch.patch_id} className="rounded-md border border-amber-100 bg-white p-3">
                        <div className="font-bold text-slate-900">{patch.patch_id}</div>
                        <div className="mt-1 text-xs text-slate-600">{patch.reason || "Review suggested patch before applying."}</div>
                        <div className="mt-1 text-xs text-slate-500">Review ID: {patch.review_id || "pending"}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {experimentBindings && (
                <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <strong>Experiment claim bindings:</strong> {asCount(experimentBindings.summary?.bound)} bound, {asCount(experimentBindings.summary?.weakly_bound)} weak, {asCount(experimentBindings.summary?.unbound)} unbound.
                      <p className="mt-1 text-xs text-emerald-800">Bindings trace manuscript sentences to local experiment metrics, result claims, and output files. They are traceability links, not scientific proof.</p>
                    </div>
                    <span className="rounded-full border border-emerald-300 bg-white px-3 py-1 text-xs font-bold">{experimentBindings.manuscript_file}</span>
                  </div>
                </div>
              )}
              {citationBindings && (
                <div className="mb-4 rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <strong>Paper citation bindings:</strong> {asCount(citationBindings.summary?.bound)} source-bound, {asCount(citationBindings.summary?.weak_binding)} weak, {asCount(citationBindings.summary?.unbound)} unbound, {asCount(citationBindings.summary?.formal_reference_available)} formal references.
                      <p className="mt-1 text-xs text-sky-800">Citation bindings connect manuscript sentences to local source passages and approved-reference state. Source-passage-only citations are not formal citation verification.</p>
                    </div>
                    <span className="rounded-full border border-sky-300 bg-white px-3 py-1 text-xs font-bold">{citationBindings.binding_file}</span>
                  </div>
                </div>
              )}
              {compileReport && (
                <div className="mb-4 rounded-lg border border-purple-200 bg-purple-50 p-4 text-sm text-purple-900">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <strong>LaTeX/PDF pipeline:</strong> {compileReport.compile_status}; compiled={compileReport.compiled_pdf ? "yes" : "no"}; preview={compileReport.preview_pdf_generated ? "yes" : "no"}.
                      <p className="mt-1 text-xs text-purple-800">A preview PDF is not a publication-ready LaTeX compilation. Review compile warnings before external use.</p>
                    </div>
                    <span className="rounded-full border border-purple-300 bg-white px-3 py-1 text-xs font-bold">{compileReport.pdf_file || compileReport.preview_pdf_file || compileReport.relative_path}</span>
                  </div>
                </div>
              )}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 p-4">
                  <h4 className="font-black text-slate-950">Manuscript artifacts</h4>
                  <ul className="mt-3 space-y-2 text-sm text-slate-700">
                    <li><strong>Markdown:</strong> {manuscriptFile || "manuscript/auto_scientist_paper.md will appear after a successful run"}</li>
                    <li><strong>LaTeX:</strong> {latexFile || "manuscript/auto_scientist_paper.tex will appear after export"}</li>
                    <li><strong>Latest run:</strong> {getRecordString(latestRun, "run_id") || "—"}</li>
                    <li><strong>Strategy:</strong> {getRecordString(latestRun, "generated_code_strategy") || status?.generated_code_strategy || "—"}</li>
                  </ul>
                </div>
                <div className="rounded-lg border border-slate-200 p-4">
                  <h4 className="font-black text-slate-950">Reviewer outcome</h4>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <MiniStat label="Decision" value={String(status?.review?.overall_decision || "—")} tone="warn" />
                    <MiniStat label="Sandbox failures" value={asCount(sandboxFailures)} tone={sandboxFailures ? "warn" : "good"} />
                  </div>
                  <p className="mt-3 text-sm text-slate-600">Automatically written manuscripts remain drafts. Claim audit, reviewer simulation, and human review must happen before external use.</p>
                </div>
              </div>
            </Panel>
          )}

          {activeTab === "trust" && (
            <Panel title="Trust Package & Approval">
              <div className="grid gap-4 md:grid-cols-3">
                <MiniStat label="Review items" value={asCount(reviewSummary.total)} />
                <MiniStat label="Pending" value={asCount(reviewSummary.pending)} tone={reviewSummary.pending ? "warn" : "good"} />
                <MiniStat label="Blocking" value={asCount(reviewSummary.blocking)} tone={reviewSummary.blocking ? "warn" : "good"} />
              </div>
              <div className="mt-5 space-y-3">
                {snapshot.queue?.items?.slice(0, 8).map((item) => (
                  <div key={item.review_id} className="rounded-lg border border-slate-200 p-3 text-sm">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h4 className="font-black text-slate-950">{item.title}</h4>
                        <p className="mt-1 text-slate-600">{item.description}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.artifact_path}</p>
                      </div>
                      <span className={`rounded-full border px-3 py-1 text-xs font-bold ${statusBadge(item.severity)}`}>{item.severity}</span>
                    </div>
                  </div>
                )) || <p className="rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-600">No human-review queue loaded yet.</p>}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </section>
  );
}
