import type {
  AnalysisComparison,
  AnalysisProvenance,
  AnalysisTimeline,
  AgentIterativeLoopResult,
  AgentRunRecord,
  AutoScientistGeneratedCodeApproval,
  AutoScientistGeneratedCodeProposal,
  AutoScientistGeneratedCodeRerun,
  AutoScientistExperimentClaimBindings,
  AutoScientistExperimentTree,
  AutoScientistExperimentTreeRerun,
  AutoScientistExperimentTreeSelection,
  AutoScientistPaperRewrite,
  AutoScientistPaperCitationBindings,
  AutoScientistPaperCompileReport,
  AutoScientistTreeRevisionApplication,
  AutoScientistTreeRevisionPlan,
  AutoScientistIdeas,
  AutoScientistRun,
  AutoScientistStatus,
  AuditExport,
  AuditFileManifest,
  AuditFilteredExport,
  AuditFilteredExportReport,
  AuditFilteredExportRequest,
  AuditFilteredExportSummary,
  AuditExportReport,
  AuditExportSummary,
  AuditLogEntry,
  BibTeXResponse,
  CitationGroundingReport,
  CitationSupportReport,
  ClaimAuditReport,
  ClaimAlignment,
  EvidenceClaim,
  EvidenceTrustPackage,
  EvidenceClaimReviewStatus,
  EvidenceClaimReviewsResponse,
  FigureProvenanceRecord,
  HumanReviewQueue,
  IssueResolution,
  IssueResolutionReview,
  IssueResolutionReviewRequest,
  LLMCallLogEntry,
  LLMStatus,
  LLMTestResult,
  LiteratureHistoryEntry,
  LiteratureMetadataLookupResponse,
  LiteratureMetadataBatchReview,
  LiteratureMetadataDiffReport,
  MetadataRevertPreview,
  LiteratureMetadataRevertSuggestion,
  MetadataReviewActionValue,
  MetadataReviewActionsResponse,
  LiteraturePatch,
  LiteratureRAGAnswer,
  LiteratureRAGChunk,
  LiteratureRAGIndex,
  RAGChunkQualityReport,
  RAGRetrievalEvalReport,
  RAGRetrievalEvalSet,
  LiteratureRecord,
  ManuscriptDiff,
  ManuscriptDiffPreview,
  ManuscriptPatch,
  ManuscriptPatchConfirmRequest,
  ManuscriptPatchConfirmResponse,
  ManuscriptPatchItemEditRequest,
  ManuscriptPatchPreview,
  ManuscriptReferencesPreview,
  ManuscriptReferencesStatus,
  ManuscriptVersionContent,
  ManuscriptVersionHistory,
  OutputContent,
  OutputItem,
  PatchConflictReport,
  PatchItemSafetyResponse,
  PatchMergeConfirmRequest,
  PatchMergeConfirmResponse,
  PatchMergePreview,
  PDFQualityReport,
  PDFPageTextPreviewResponse,
  PDFPageReviewsResponse,
  PromptRegistry,
  ProjectJob,
  ProjectJobEvents,
  ProjectJobLog,
  PaperWriterPlan,
  PaperWriterOutline,
  PaperWriterDraft,
  PaperWriterLatexExport,
  PaperWriterStatus,
  ProjectExportInfo,
  ProjectDetail,
  ProjectRead,
  ProductionScaffoldReport,
  ReferenceApproval,
  ReferenceApprovalDecision,
  ReferenceApprovalResponse,
  ReferenceApprovalSummaryResponse,
  ReferenceVerificationProvider,
  ReferenceVerificationResult,
  ReferenceVerificationRunResponse,
  ReferenceVerificationSummaryResponse,
  RevisionDecision,
  RevisionPlan,
  RevisionDecisionPatch,
  RevisionDiffHumanStatus,
  RevisionDiffReviewsResponse,
  RevisionLineDiff,
  ReviewerClosureSummary,
  RunHistory,
  SentenceIssue,
  SourcePassageEvidenceReport,
  ReadinessReport,
  StatisticalAssistantReport,
  TrustSummary,
  AuditVerifyResult,
  VersionLineage,
  WorkflowRunResponse,
  WorkspaceExportManifest
} from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function listProjects(): Promise<ProjectRead[]> {
  return request<ProjectRead[]>("/api/projects");
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/api/projects/${projectId}`);
}

export async function getLLMStatus(): Promise<LLMStatus> {
  return request<LLMStatus>("/api/system/llm/status");
}

export async function testLLM(prompt: string, promptVersion = "literature_answer_v1"): Promise<LLMTestResult> {
  return request<LLMTestResult>("/api/system/llm/test", {
    method: "POST",
    body: JSON.stringify({ prompt, prompt_version: promptVersion })
  });
}

export async function getPromptRegistry(): Promise<PromptRegistry> {
  return request<PromptRegistry>("/api/system/prompts");
}

export async function getProductionScaffold(): Promise<ProductionScaffoldReport> {
  return request<ProductionScaffoldReport>("/api/system/production-scaffold");
}

export async function getLLMCalls(projectId: string): Promise<LLMCallLogEntry[]> {
  return request<LLMCallLogEntry[]>(`/api/projects/${projectId}/llm/calls`);
}

export async function buildLiteratureRAG(projectId: string): Promise<LiteratureRAGIndex> {
  return request<LiteratureRAGIndex>(`/api/projects/${projectId}/literature/rag/build`, {
    method: "POST"
  });
}

export async function askLiteratureRAG(
  projectId: string,
  question: string,
  topK = 5,
  retrievalMode = "local_hybrid"
): Promise<LiteratureRAGAnswer> {
  return request<LiteratureRAGAnswer>(`/api/projects/${projectId}/literature/rag/ask`, {
    method: "POST",
    body: JSON.stringify({ question, top_k: topK, retrieval_mode: retrievalMode })
  });
}

export async function getLiteratureRAGChunks(projectId: string): Promise<LiteratureRAGChunk[]> {
  return request<LiteratureRAGChunk[]>(`/api/projects/${projectId}/literature/rag/chunks`);
}

export async function getLiteratureRAGAnswers(projectId: string): Promise<LiteratureRAGAnswer[]> {
  return request<LiteratureRAGAnswer[]>(`/api/projects/${projectId}/literature/rag/answers`);
}

export async function runClaimAudit(
  projectId: string,
  manuscriptText?: string,
  retrievalMode = "local_hybrid_fts"
): Promise<ClaimAuditReport> {
  return request<ClaimAuditReport>(`/api/projects/${projectId}/manuscript/claim-audit`, {
    method: "POST",
    body: JSON.stringify({ manuscript_text: manuscriptText, retrieval_mode: retrievalMode })
  });
}

export async function getClaimAudit(projectId: string): Promise<ClaimAuditReport> {
  return request<ClaimAuditReport>(`/api/projects/${projectId}/manuscript/claim-audit`);
}

export async function createRevisionPlan(projectId: string): Promise<RevisionPlan> {
  return request<RevisionPlan>(`/api/projects/${projectId}/manuscript/revision-plan`, {
    method: "POST"
  });
}

export async function getRevisionPlan(projectId: string): Promise<RevisionPlan> {
  return request<RevisionPlan>(`/api/projects/${projectId}/manuscript/revision-plan`);
}

export async function getHumanReviewQueue(projectId: string): Promise<HumanReviewQueue> {
  return request<HumanReviewQueue>(`/api/projects/${projectId}/human-review-queue`);
}

export async function decideHumanReviewItem(
  projectId: string,
  reviewId: string,
  decision: "approved" | "rejected" | "edited" | "dismissed",
  reason = ""
): Promise<HumanReviewQueue> {
  return request<HumanReviewQueue>(`/api/projects/${projectId}/human-review-queue/${reviewId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, reason })
  });
}

export async function createAutoScientistIdeas(
  projectId: string,
  payload: { topic?: string; research_question?: string; max_ideas?: number } = {}
): Promise<AutoScientistIdeas> {
  return request<AutoScientistIdeas>(`/api/projects/${projectId}/auto-scientist/ideas`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAutoScientistIdeas(projectId: string): Promise<AutoScientistIdeas> {
  return request<AutoScientistIdeas>(`/api/projects/${projectId}/auto-scientist/ideas`);
}

export async function runAutoScientist(
  projectId: string,
  payload: {
    topic?: string;
    research_question?: string;
    max_ideas?: number;
    max_experiments_per_idea?: number;
    paper_type?: string;
    retrieval_mode?: string;
    write_paper?: boolean;
    export_latex?: boolean;
    copilot_mode?: "off" | "advisory" | "strict";
    allow_generated_code_experiments?: boolean;
    generated_code_timeout_seconds?: number;
    generated_code_max_memory_mb?: number;
    generated_code_sandbox_mode?: "subprocess" | "docker";
    generated_code_docker_image?: string;
    generated_code_source_mode?: "deterministic" | "mock_llm" | "live_llm";
    generated_code_strategy?: "lexical_diagnostics" | "retrieval_ablation" | "claim_support_matrix" | "descriptive_table_profile";
    generated_code_requires_approval?: boolean | null;
    generated_code_approved?: boolean;
    enable_generated_code_revision_loop?: boolean;
    generated_code_revision_rounds?: number;
    enable_experiment_tree_search?: boolean;
    experiment_tree_max_depth?: number;
    experiment_tree_branching_factor?: number;
  } = {}
): Promise<AutoScientistRun> {
  return request<AutoScientistRun>(`/api/projects/${projectId}/auto-scientist/run`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAutoScientistStatus(projectId: string): Promise<AutoScientistStatus> {
  return request<AutoScientistStatus>(`/api/projects/${projectId}/auto-scientist/status`);
}

export async function runAutoScientistJob(
  projectId: string,
  payload: Parameters<typeof runAutoScientist>[1] = {}
): Promise<ProjectJob> {
  return request<ProjectJob>(`/api/projects/${projectId}/jobs/auto-scientist/run`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function startAutoScientistJob(
  projectId: string,
  payload: Parameters<typeof runAutoScientist>[1] = {}
): Promise<ProjectJob> {
  return request<ProjectJob>(`/api/projects/${projectId}/jobs/auto-scientist/start`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getProjectJobs(projectId: string, limit = 50): Promise<ProjectJob[]> {
  return request<ProjectJob[]>(`/api/projects/${projectId}/jobs?limit=${limit}`);
}

export async function getProjectJob(projectId: string, jobId: string): Promise<ProjectJob> {
  return request<ProjectJob>(`/api/projects/${projectId}/jobs/${jobId}`);
}

export async function getProjectJobLog(projectId: string, jobId: string): Promise<ProjectJobLog> {
  return request<ProjectJobLog>(`/api/projects/${projectId}/jobs/${jobId}/log`);
}

export async function getProjectJobEvents(projectId: string, jobId: string, sinceSequence = 0): Promise<ProjectJobEvents> {
  return request<ProjectJobEvents>(`/api/projects/${projectId}/jobs/${jobId}/events?since_sequence=${sinceSequence}`);
}

export async function cancelProjectJob(projectId: string, jobId: string, reason = "User requested cancellation from Auto Scientist Workbench."): Promise<ProjectJob> {
  return request<ProjectJob>(`/api/projects/${projectId}/jobs/${jobId}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason })
  });
}

export async function getAutoScientistRuns(projectId: string): Promise<Array<Record<string, unknown>>> {
  return request<Array<Record<string, unknown>>>(`/api/projects/${projectId}/auto-scientist/runs`);
}

export async function getAutoScientistExperimentTree(projectId: string): Promise<AutoScientistExperimentTree> {
  return request<AutoScientistExperimentTree>(`/api/projects/${projectId}/auto-scientist/experiment-tree/nodes`);
}

export async function selectAutoScientistExperimentTreeNode(
  projectId: string,
  payload: { node_id: string; reason?: string }
): Promise<AutoScientistExperimentTreeSelection> {
  return request<AutoScientistExperimentTreeSelection>(`/api/projects/${projectId}/auto-scientist/experiment-tree/select`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function rerunAutoScientistExperimentTreeNode(
  projectId: string,
  payload: { node_id: string; sandbox_mode?: "subprocess" | "docker"; docker_image?: string; timeout_seconds?: number; max_memory_mb?: number }
): Promise<AutoScientistExperimentTreeRerun> {
  return request<AutoScientistExperimentTreeRerun>(`/api/projects/${projectId}/auto-scientist/experiment-tree/rerun-node`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function rewriteAutoScientistPaperFromTree(
  projectId: string,
  payload: { node_id?: string; reason?: string } = {}
): Promise<AutoScientistPaperRewrite> {
  return request<AutoScientistPaperRewrite>(`/api/projects/${projectId}/auto-scientist/experiment-tree/rewrite-paper`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}


export async function getAutoScientistExperimentClaimBindings(projectId: string): Promise<AutoScientistExperimentClaimBindings> {
  return request<AutoScientistExperimentClaimBindings>(`/api/projects/${projectId}/auto-scientist/experiment-claim-bindings`);
}

export async function createAutoScientistExperimentClaimBindings(
  projectId: string,
  payload: { manuscript_relative_path?: string | null; node_id?: string | null; reason?: string; top_k?: number } = {}
): Promise<AutoScientistExperimentClaimBindings> {
  return request<AutoScientistExperimentClaimBindings>(`/api/projects/${projectId}/auto-scientist/experiment-claim-bindings`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAutoScientistPaperCitationBindings(projectId: string): Promise<AutoScientistPaperCitationBindings> {
  return request<AutoScientistPaperCitationBindings>(`/api/projects/${projectId}/auto-scientist/paper-citation-bindings`);
}

export async function createAutoScientistPaperCitationBindings(
  projectId: string,
  payload: { manuscript_relative_path?: string | null; retrieval_mode?: string; top_k?: number } = {}
): Promise<AutoScientistPaperCitationBindings> {
  return request<AutoScientistPaperCitationBindings>(`/api/projects/${projectId}/auto-scientist/paper-citation-bindings`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAutoScientistPaperCompileReport(projectId: string): Promise<AutoScientistPaperCompileReport> {
  return request<AutoScientistPaperCompileReport>(`/api/projects/${projectId}/auto-scientist/paper-compile`);
}

export async function compileAutoScientistPaper(
  projectId: string,
  payload: { manuscript_tex_relative_path?: string | null; engine?: "auto" | "pdflatex" | "tectonic" | "none"; timeout_seconds?: number; generate_preview_pdf?: boolean } = {}
): Promise<AutoScientistPaperCompileReport> {
  return request<AutoScientistPaperCompileReport>(`/api/projects/${projectId}/auto-scientist/paper-compile`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}


export async function getAutoScientistTreeRevisionPlan(projectId: string): Promise<AutoScientistTreeRevisionPlan> {
  return request<AutoScientistTreeRevisionPlan>(`/api/projects/${projectId}/auto-scientist/experiment-tree/revision-plan`);
}

export async function createAutoScientistTreeRevisionPlan(
  projectId: string,
  payload: { node_id?: string; reason?: string } = {}
): Promise<AutoScientistTreeRevisionPlan> {
  return request<AutoScientistTreeRevisionPlan>(`/api/projects/${projectId}/auto-scientist/experiment-tree/revision-plan`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function applyAutoScientistTreeRevision(
  projectId: string,
  payload: { patch_ids?: string[]; reason?: string; require_human_approval?: boolean; rerun_claim_audit?: boolean; regenerate_trust_package?: boolean } = {}
): Promise<AutoScientistTreeRevisionApplication> {
  return request<AutoScientistTreeRevisionApplication>(`/api/projects/${projectId}/auto-scientist/experiment-tree/apply-revision`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}


export async function getAutoScientistGeneratedCodeApprovals(
  projectId: string
): Promise<AutoScientistGeneratedCodeApproval[]> {
  return request<AutoScientistGeneratedCodeApproval[]>(`/api/projects/${projectId}/auto-scientist/generated-code/approvals`);
}

export async function getAutoScientistGeneratedCodeProposals(
  projectId: string
): Promise<AutoScientistGeneratedCodeProposal[]> {
  return request<AutoScientistGeneratedCodeProposal[]>(`/api/projects/${projectId}/auto-scientist/generated-code/proposals`);
}

export async function approveAutoScientistGeneratedCode(
  projectId: string,
  payload: { run_id: string; experiment_id: string; source_hash?: string; decision: "approved" | "rejected"; reason?: string }
): Promise<AutoScientistGeneratedCodeApproval> {
  return request<AutoScientistGeneratedCodeApproval>(`/api/projects/${projectId}/auto-scientist/generated-code/approvals`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function rerunAutoScientistGeneratedCode(
  projectId: string,
  payload: { run_id: string; experiment_id: string; source_hash: string; sandbox_mode?: "subprocess" | "docker"; docker_image?: string; timeout_seconds?: number; max_memory_mb?: number }
): Promise<AutoScientistGeneratedCodeRerun> {
  return request<AutoScientistGeneratedCodeRerun>(`/api/projects/${projectId}/auto-scientist/generated-code/rerun`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}


export async function createPaperWriterPlan(
  projectId: string,
  payload: { paper_type?: string; topic?: string; research_question?: string; retrieval_mode?: string } = {}
): Promise<PaperWriterPlan> {
  return request<PaperWriterPlan>(`/api/projects/${projectId}/paper-writer/plan`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getPaperWriterPlan(projectId: string): Promise<PaperWriterPlan> {
  return request<PaperWriterPlan>(`/api/projects/${projectId}/paper-writer/plan`);
}

export async function createPaperWriterOutline(
  projectId: string,
  retrievalMode = "local_hybrid_fts"
): Promise<PaperWriterOutline> {
  return request<PaperWriterOutline>(`/api/projects/${projectId}/paper-writer/outline`, {
    method: "POST",
    body: JSON.stringify({ retrieval_mode: retrievalMode })
  });
}

export async function getPaperWriterOutline(projectId: string): Promise<PaperWriterOutline> {
  return request<PaperWriterOutline>(`/api/projects/${projectId}/paper-writer/outline`);
}

export async function createPaperWriterDraft(
  projectId: string,
  retrievalMode = "local_hybrid_fts",
  runClaimAuditAfter = true
): Promise<PaperWriterDraft> {
  return request<PaperWriterDraft>(`/api/projects/${projectId}/paper-writer/draft`, {
    method: "POST",
    body: JSON.stringify({ retrieval_mode: retrievalMode, run_claim_audit_after: runClaimAuditAfter })
  });
}

export async function getPaperWriterDraft(projectId: string): Promise<PaperWriterStatus> {
  return request<PaperWriterStatus>(`/api/projects/${projectId}/paper-writer/draft`);
}

export async function exportPaperWriterLatex(projectId: string): Promise<PaperWriterLatexExport> {
  return request<PaperWriterLatexExport>(`/api/projects/${projectId}/paper-writer/export-latex`, {
    method: "POST",
    body: JSON.stringify({ compile_pdf: false })
  });
}

export async function getPaperWriterStatus(projectId: string): Promise<PaperWriterStatus> {
  return request<PaperWriterStatus>(`/api/projects/${projectId}/paper-writer/status`);
}

export async function getRAGChunkQuality(projectId: string): Promise<RAGChunkQualityReport> {
  return request<RAGChunkQualityReport>(`/api/projects/${projectId}/literature/rag/quality`);
}

export async function getRAGRetrievalEvalSet(projectId: string): Promise<RAGRetrievalEvalSet> {
  return request<RAGRetrievalEvalSet>(`/api/projects/${projectId}/literature/rag/eval-set`);
}

export async function evaluateRAGRetrieval(projectId: string): Promise<RAGRetrievalEvalReport> {
  return request<RAGRetrievalEvalReport>(`/api/projects/${projectId}/literature/rag/evaluate`, {
    method: "POST"
  });
}

export async function getRAGRetrievalEvaluation(projectId: string): Promise<RAGRetrievalEvalReport> {
  return request<RAGRetrievalEvalReport>(`/api/projects/${projectId}/literature/rag/evaluation`);
}

export async function getSourcePassageEvidence(projectId: string): Promise<SourcePassageEvidenceReport> {
  return request<SourcePassageEvidenceReport>(
    `/api/projects/${projectId}/provenance/source-passage-evidence`
  );
}

export async function runMetadataLookup(
  projectId: string,
  provider = "mock_fixture"
): Promise<LiteratureMetadataLookupResponse> {
  return request<LiteratureMetadataLookupResponse>(
    `/api/projects/${projectId}/literature/metadata-lookup`,
    {
      method: "POST",
      body: JSON.stringify({ provider })
    }
  );
}

export async function getMetadataLookupResults(
  projectId: string
): Promise<LiteratureMetadataLookupResponse> {
  return request<LiteratureMetadataLookupResponse>(
    `/api/projects/${projectId}/literature/metadata-lookup/results`
  );
}

export async function generateBibTeX(projectId: string): Promise<BibTeXResponse> {
  return request<BibTeXResponse>(`/api/projects/${projectId}/literature/bibtex/generate`, {
    method: "POST"
  });
}

export async function getBibTeX(projectId: string): Promise<BibTeXResponse> {
  return request<BibTeXResponse>(`/api/projects/${projectId}/literature/bibtex`);
}

export async function getCitationSupport(projectId: string): Promise<CitationSupportReport> {
  return request<CitationSupportReport>(`/api/projects/${projectId}/provenance/citation-support`);
}

export async function runReferenceVerification(
  projectId: string,
  provider: ReferenceVerificationProvider = "mock_fixture",
  literatureId?: string
): Promise<ReferenceVerificationRunResponse> {
  return request<ReferenceVerificationRunResponse>(
    `/api/projects/${projectId}/literature/reference-verification/run`,
    {
      method: "POST",
      body: JSON.stringify({ provider, literature_id: literatureId })
    }
  );
}

export async function getReferenceVerificationResults(
  projectId: string
): Promise<ReferenceVerificationResult[]> {
  return request<ReferenceVerificationResult[]>(
    `/api/projects/${projectId}/literature/reference-verification/results`
  );
}

export async function getReferenceVerificationSummary(
  projectId: string
): Promise<ReferenceVerificationSummaryResponse> {
  return request<ReferenceVerificationSummaryResponse>(
    `/api/projects/${projectId}/literature/reference-verification/summary`
  );
}

export async function approveReferenceVerification(
  projectId: string,
  verificationId: string,
  decision: ReferenceApprovalDecision,
  reason?: string,
  applyToLiteratureIndex = false
): Promise<ReferenceApprovalResponse> {
  return request<ReferenceApprovalResponse>(
    `/api/projects/${projectId}/literature/reference-verification/${verificationId}/approval`,
    {
      method: "POST",
      body: JSON.stringify({
        decision,
        reason,
        apply_to_literature_index: applyToLiteratureIndex
      })
    }
  );
}

export async function getReferenceApprovals(projectId: string): Promise<ReferenceApproval[]> {
  return request<ReferenceApproval[]>(`/api/projects/${projectId}/literature/reference-approvals`);
}

export async function getReferenceApprovalSummary(
  projectId: string
): Promise<ReferenceApprovalSummaryResponse> {
  return request<ReferenceApprovalSummaryResponse>(
    `/api/projects/${projectId}/literature/reference-approval-summary`
  );
}

export async function getCitationGrounding(projectId: string): Promise<CitationGroundingReport> {
  return request<CitationGroundingReport>(
    `/api/projects/${projectId}/provenance/citation-grounding`
  );
}

export async function getManuscriptReferencesStatus(
  projectId: string
): Promise<ManuscriptReferencesStatus> {
  return request<ManuscriptReferencesStatus>(
    `/api/projects/${projectId}/manuscript/references/status`
  );
}

export async function getManuscriptReferencesPreview(
  projectId: string
): Promise<ManuscriptReferencesPreview> {
  return request<ManuscriptReferencesPreview>(
    `/api/projects/${projectId}/manuscript/references/preview`
  );
}

export async function runWorkflow(projectId: string): Promise<WorkflowRunResponse> {
  return request<WorkflowRunResponse>(`/api/projects/${projectId}/workflow/run`, {
    method: "POST"
  });
}

export async function runIterativeResearchLoop(
  projectId: string,
  maxRounds = 2
): Promise<AgentIterativeLoopResult> {
  return request<AgentIterativeLoopResult>(`/api/projects/${projectId}/agent/iterative-loop`, {
    method: "POST",
    body: JSON.stringify({ max_rounds: maxRounds })
  });
}

export async function getLatestIterativeResearchLoop(projectId: string): Promise<AgentIterativeLoopResult> {
  return request<AgentIterativeLoopResult>(`/api/projects/${projectId}/agent/iterative-loop/latest`);
}

export async function getAgentRuns(projectId: string): Promise<AgentRunRecord[]> {
  return request<AgentRunRecord[]>(`/api/projects/${projectId}/agent/runs`);
}

export async function getOutput(projectId: string, outputId: string): Promise<OutputContent> {
  return request<OutputContent>(`/api/projects/${projectId}/outputs/${outputId}`);
}

export function getOutputFileUrl(projectId: string, outputId: string): string {
  return `${API_BASE}/api/projects/${projectId}/outputs/${outputId}/file`;
}

export async function getEvidence(projectId: string): Promise<EvidenceClaim[]> {
  return request<EvidenceClaim[]>(`/api/projects/${projectId}/evidence`);
}

export async function getEvidenceClaimReviews(projectId: string): Promise<EvidenceClaimReviewsResponse> {
  return request<EvidenceClaimReviewsResponse>(
    `/api/projects/${projectId}/evidence/claim-reviews`
  );
}

export async function reviewEvidenceClaim(
  projectId: string,
  claimId: string,
  humanStatus: EvidenceClaimReviewStatus,
  reason?: string
): Promise<EvidenceClaimReviewsResponse["reviews"][number] & { summary: EvidenceClaimReviewsResponse["summary"] }> {
  return request<EvidenceClaimReviewsResponse["reviews"][number] & { summary: EvidenceClaimReviewsResponse["summary"] }>(
    `/api/projects/${projectId}/evidence/claims/${claimId}/review`,
    {
      method: "POST",
      body: JSON.stringify({ human_status: humanStatus, reason })
    }
  );
}

export async function getFigureProvenance(projectId: string): Promise<FigureProvenanceRecord[]> {
  return request<FigureProvenanceRecord[]>(`/api/projects/${projectId}/figures/provenance`);
}

export async function getClaimAlignment(projectId: string): Promise<ClaimAlignment> {
  return request<ClaimAlignment>(`/api/projects/${projectId}/claim-alignment`);
}

export async function getSentenceIssues(projectId: string): Promise<SentenceIssue[]> {
  return request<SentenceIssue[]>(`/api/projects/${projectId}/review/sentence-issues`);
}

export async function getRevisionDecisions(projectId: string): Promise<RevisionDecision[]> {
  return request<RevisionDecision[]>(`/api/projects/${projectId}/review/revision-decisions`);
}

export async function createRevisionDecision(
  projectId: string,
  issueId: string,
  patch: RevisionDecisionPatch
): Promise<RevisionDecision> {
  return request<RevisionDecision>(
    `/api/projects/${projectId}/review/sentence-issues/${issueId}/decision`,
    {
      method: "POST",
      body: JSON.stringify(patch)
    }
  );
}

export async function generateManuscriptPatch(
  projectId: string,
  sourceManuscript = "manuscript/draft.md"
): Promise<ManuscriptPatch> {
  return request<ManuscriptPatch>(`/api/projects/${projectId}/manuscript/patches/generate`, {
    method: "POST",
    body: JSON.stringify({ source_manuscript: sourceManuscript })
  });
}

export async function getManuscriptPatches(projectId: string): Promise<ManuscriptPatch[]> {
  return request<ManuscriptPatch[]>(`/api/projects/${projectId}/manuscript/patches`);
}

export async function getManuscriptPatch(
  projectId: string,
  patchId: string
): Promise<ManuscriptPatch> {
  return request<ManuscriptPatch>(`/api/projects/${projectId}/manuscript/patches/${patchId}`);
}

export async function getManuscriptPatchPreview(
  projectId: string,
  patchId: string
): Promise<ManuscriptPatchPreview> {
  return request<ManuscriptPatchPreview>(
    `/api/projects/${projectId}/manuscript/patches/${patchId}/preview`
  );
}

export async function confirmManuscriptPatch(
  projectId: string,
  patchId: string,
  payload: ManuscriptPatchConfirmRequest
): Promise<ManuscriptPatchConfirmResponse> {
  return request<ManuscriptPatchConfirmResponse>(
    `/api/projects/${projectId}/manuscript/patches/${patchId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function editManuscriptPatchItem(
  projectId: string,
  patchId: string,
  patchItemId: string,
  payload: ManuscriptPatchItemEditRequest
): Promise<ManuscriptPatch> {
  return request<ManuscriptPatch>(
    `/api/projects/${projectId}/manuscript/patches/${patchId}/items/${patchItemId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    }
  );
}

export async function safetyCheckManuscriptPatchItem(
  projectId: string,
  patchId: string,
  patchItemId: string
): Promise<PatchItemSafetyResponse> {
  return request<PatchItemSafetyResponse>(
    `/api/projects/${projectId}/manuscript/patches/${patchId}/items/${patchItemId}/safety-check`,
    {
      method: "POST"
    }
  );
}

export async function checkPatchConflicts(
  projectId: string,
  patchIds: string[]
): Promise<PatchConflictReport> {
  return request<PatchConflictReport>(
    `/api/projects/${projectId}/manuscript/patches/conflicts/check`,
    {
      method: "POST",
      body: JSON.stringify({ patch_ids: patchIds })
    }
  );
}

export async function generatePatchMergePreview(
  projectId: string,
  patchIds: string[]
): Promise<PatchMergePreview> {
  return request<PatchMergePreview>(
    `/api/projects/${projectId}/manuscript/patches/merge-preview`,
    {
      method: "POST",
      body: JSON.stringify({ patch_ids: patchIds })
    }
  );
}

export async function confirmPatchMerge(
  projectId: string,
  mergeId: string,
  payload: PatchMergeConfirmRequest
): Promise<PatchMergeConfirmResponse> {
  return request<PatchMergeConfirmResponse>(
    `/api/projects/${projectId}/manuscript/patches/merges/${mergeId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getManuscriptVersions(
  projectId: string
): Promise<ManuscriptVersionHistory> {
  return request<ManuscriptVersionHistory>(`/api/projects/${projectId}/manuscript/versions`);
}

export async function getVersionLineage(projectId: string): Promise<VersionLineage> {
  return request<VersionLineage>(`/api/projects/${projectId}/manuscript/versions/lineage`);
}

export async function getManuscriptVersion(
  projectId: string,
  versionId: string
): Promise<ManuscriptVersionContent> {
  return request<ManuscriptVersionContent>(
    `/api/projects/${projectId}/manuscript/versions/${versionId}`
  );
}

export async function generateManuscriptDiff(
  projectId: string,
  versionId: string,
  baseFile = "manuscript/draft.md"
): Promise<ManuscriptDiff> {
  return request<ManuscriptDiff>(`/api/projects/${projectId}/manuscript/diffs/generate`, {
    method: "POST",
    body: JSON.stringify({ base_file: baseFile, version_id: versionId })
  });
}

export async function getManuscriptDiffs(projectId: string): Promise<ManuscriptDiff[]> {
  return request<ManuscriptDiff[]>(`/api/projects/${projectId}/manuscript/diffs`);
}

export async function getManuscriptDiff(
  projectId: string,
  diffId: string
): Promise<ManuscriptDiff> {
  return request<ManuscriptDiff>(`/api/projects/${projectId}/manuscript/diffs/${diffId}`);
}

export async function getManuscriptDiffPreview(
  projectId: string,
  diffId: string
): Promise<ManuscriptDiffPreview> {
  return request<ManuscriptDiffPreview>(
    `/api/projects/${projectId}/manuscript/diffs/${diffId}/preview`
  );
}

export async function generateRevisionLineDiff(
  projectId: string,
  targetFile: string,
  baseFile = "manuscript/draft.md"
): Promise<RevisionLineDiff> {
  return request<RevisionLineDiff>(
    `/api/projects/${projectId}/manuscript/revision-diffs/generate`,
    {
      method: "POST",
      body: JSON.stringify({ base_file: baseFile, target_file: targetFile })
    }
  );
}

export async function getRevisionLineDiffs(projectId: string): Promise<RevisionLineDiff[]> {
  return request<RevisionLineDiff[]>(`/api/projects/${projectId}/manuscript/revision-diffs`);
}

export async function getRevisionLineDiff(
  projectId: string,
  revisionDiffId: string
): Promise<RevisionLineDiff> {
  return request<RevisionLineDiff>(
    `/api/projects/${projectId}/manuscript/revision-diffs/${revisionDiffId}`
  );
}

export async function getRevisionDiffReviews(projectId: string): Promise<RevisionDiffReviewsResponse> {
  return request<RevisionDiffReviewsResponse>(
    `/api/projects/${projectId}/manuscript/revision-diffs/reviews`
  );
}

export async function reviewRevisionDiffChange(
  projectId: string,
  revisionDiffId: string,
  changeId: string,
  humanStatus: RevisionDiffHumanStatus,
  reason?: string
): Promise<RevisionDiffReviewsResponse["reviews"][number] & { summary: RevisionDiffReviewsResponse["summary"] }> {
  return request<RevisionDiffReviewsResponse["reviews"][number] & { summary: RevisionDiffReviewsResponse["summary"] }>(
    `/api/projects/${projectId}/manuscript/revision-diffs/${revisionDiffId}/changes/${changeId}/review`,
    {
      method: "POST",
      body: JSON.stringify({ human_status: humanStatus, reason })
    }
  );
}

export async function getLiterature(projectId: string): Promise<LiteratureRecord[]> {
  return request<LiteratureRecord[]>(`/api/projects/${projectId}/literature`);
}

export async function getLiteratureHistory(projectId: string): Promise<LiteratureHistoryEntry[]> {
  return request<LiteratureHistoryEntry[]>(`/api/projects/${projectId}/literature/history`);
}

export async function getLiteratureRecordHistory(
  projectId: string,
  literatureId: string
): Promise<LiteratureHistoryEntry[]> {
  return request<LiteratureHistoryEntry[]>(
    `/api/projects/${projectId}/literature/${literatureId}/history`
  );
}

export async function patchLiterature(
  projectId: string,
  literatureId: string,
  patch: LiteraturePatch
): Promise<LiteratureRecord> {
  return request<LiteratureRecord>(`/api/projects/${projectId}/literature/${literatureId}`, {
    method: "PATCH",
    body: JSON.stringify(patch)
  });
}

export async function getLiteratureMetadataDiff(
  projectId: string
): Promise<LiteratureMetadataDiffReport> {
  return request<LiteratureMetadataDiffReport>(
    `/api/projects/${projectId}/literature/metadata-diff`
  );
}

export async function suggestLiteratureMetadataRevert(
  projectId: string,
  literatureId: string,
  field: string,
  sourceHistoryId: string
): Promise<LiteratureMetadataRevertSuggestion> {
  return request<LiteratureMetadataRevertSuggestion>(
    `/api/projects/${projectId}/literature/${literatureId}/metadata/revert-suggestion`,
    {
      method: "POST",
      body: JSON.stringify({ field, source_history_id: sourceHistoryId })
    }
  );
}

export async function previewMetadataRevert(
  projectId: string,
  literatureId: string,
  field: string,
  sourceHistoryId: string
): Promise<MetadataRevertPreview> {
  return request<MetadataRevertPreview>(
    `/api/projects/${projectId}/literature/${literatureId}/metadata/revert-preview`,
    {
      method: "POST",
      body: JSON.stringify({ field, source_history_id: sourceHistoryId })
    }
  );
}

export async function generateLiteratureMetadataBatchReview(
  projectId: string
): Promise<LiteratureMetadataBatchReview> {
  return request<LiteratureMetadataBatchReview>(
    `/api/projects/${projectId}/literature/metadata-review-batch`,
    {
      method: "POST"
    }
  );
}

export async function getMetadataReviewActions(projectId: string): Promise<MetadataReviewActionsResponse> {
  return request<MetadataReviewActionsResponse>(
    `/api/projects/${projectId}/literature/metadata-review-actions`
  );
}

export async function reviewMetadataChange(
  projectId: string,
  literatureId: string,
  field: string,
  action: MetadataReviewActionValue,
  sourceHistoryId: string,
  reason?: string
): Promise<MetadataReviewActionsResponse["actions"][number] & { summary: MetadataReviewActionsResponse["summary"] }> {
  return request<MetadataReviewActionsResponse["actions"][number] & { summary: MetadataReviewActionsResponse["summary"] }>(
    `/api/projects/${projectId}/literature/${literatureId}/metadata-review`,
    {
      method: "POST",
      body: JSON.stringify({
        field,
        action,
        source_history_id: sourceHistoryId,
        reason
      })
    }
  );
}

export async function getAnalysisProvenance(projectId: string): Promise<AnalysisProvenance> {
  return request<AnalysisProvenance>(`/api/projects/${projectId}/analysis/provenance`);
}

export async function getStatisticalAssistant(
  projectId: string
): Promise<StatisticalAssistantReport> {
  return request<StatisticalAssistantReport>(
    `/api/projects/${projectId}/analysis/statistical-assistant`
  );
}

export async function generateStatisticalAssistant(
  projectId: string
): Promise<StatisticalAssistantReport> {
  return request<StatisticalAssistantReport>(
    `/api/projects/${projectId}/analysis/statistical-assistant/generate`,
    { method: "POST" }
  );
}

export async function getPDFQualityReport(projectId: string): Promise<PDFQualityReport> {
  return request<PDFQualityReport>(`/api/projects/${projectId}/literature/pdf-quality-report`);
}

export async function getPDFPageReviews(projectId: string): Promise<PDFPageReviewsResponse> {
  return request<PDFPageReviewsResponse>(`/api/projects/${projectId}/literature/pdf-page-reviews`);
}

export async function getPDFPageTextPreview(
  projectId: string,
  sourceFile?: string,
  pageNumber?: number
): Promise<PDFPageTextPreviewResponse> {
  const params = new URLSearchParams();
  if (sourceFile) params.set("source_file", sourceFile);
  if (pageNumber) params.set("page_number", String(pageNumber));
  const query = params.toString();
  return request<PDFPageTextPreviewResponse>(
    `/api/projects/${projectId}/literature/pdf-page-text-preview${query ? `?${query}` : ""}`
  );
}

export async function reviewPDFPage(
  projectId: string,
  sourceFile: string,
  pageNumber: number,
  humanStatus: PDFPageReviewsResponse["reviews"][number]["human_status"],
  reason?: string
): Promise<PDFPageReviewsResponse["reviews"][number] & { summary: PDFPageReviewsResponse["summary"] }> {
  return request<PDFPageReviewsResponse["reviews"][number] & { summary: PDFPageReviewsResponse["summary"] }>(
    `/api/projects/${projectId}/literature/pdf-page-review`,
    {
      method: "POST",
      body: JSON.stringify({
        source_file: sourceFile,
        page_number: pageNumber,
        human_status: humanStatus,
        reason
      })
    }
  );
}

export async function generateAnalysisComparison(
  projectId: string,
  baseProvenance = "analysis/analysis_provenance.json",
  targetProvenance = "analysis/analysis_provenance.json"
): Promise<AnalysisComparison> {
  return request<AnalysisComparison>(`/api/projects/${projectId}/analysis/compare`, {
    method: "POST",
    body: JSON.stringify({
      base_provenance: baseProvenance,
      target_provenance: targetProvenance
    })
  });
}

export async function getAnalysisComparisons(projectId: string): Promise<AnalysisComparison[]> {
  return request<AnalysisComparison[]>(`/api/projects/${projectId}/analysis/comparisons`);
}

export async function getAnalysisComparison(
  projectId: string,
  comparisonId: string
): Promise<AnalysisComparison> {
  return request<AnalysisComparison>(
    `/api/projects/${projectId}/analysis/comparisons/${comparisonId}`
  );
}

export async function getAnalysisTimeline(projectId: string): Promise<AnalysisTimeline> {
  return request<AnalysisTimeline>(`/api/projects/${projectId}/analysis/timeline`);
}

export async function getEnhancedAnalysisTimeline(projectId: string): Promise<AnalysisTimeline> {
  return request<AnalysisTimeline>(`/api/projects/${projectId}/analysis/timeline/enhanced`);
}

export async function getTrustSummary(projectId: string): Promise<TrustSummary> {
  return request<TrustSummary>(`/api/projects/${projectId}/trust/summary`);
}

export async function getReviewerClosureSummary(projectId: string): Promise<ReviewerClosureSummary> {
  return request<ReviewerClosureSummary>(`/api/projects/${projectId}/review/closure-summary`);
}

export async function getReadinessReport(projectId: string): Promise<ReadinessReport> {
  return request<ReadinessReport>(`/api/projects/${projectId}/trust/readiness-report`);
}

export async function getProjectExport(projectId: string): Promise<ProjectExportInfo> {
  return request<ProjectExportInfo>(`/api/projects/${projectId}/export/zip`);
}

export async function createProjectExport(projectId: string): Promise<ProjectExportInfo> {
  return request<ProjectExportInfo>(`/api/projects/${projectId}/export/zip`, {
    method: "POST"
  });
}

export async function getWorkspaceExport(projectId: string): Promise<WorkspaceExportManifest> {
  return request<WorkspaceExportManifest>(`/api/projects/${projectId}/export/workspace`);
}

export async function createWorkspaceExport(projectId: string): Promise<WorkspaceExportManifest> {
  return request<WorkspaceExportManifest>(`/api/projects/${projectId}/export/workspace`, {
    method: "POST"
  });
}

export async function getEvidenceTrustPackage(projectId: string): Promise<EvidenceTrustPackage> {
  return request<EvidenceTrustPackage>(`/api/projects/${projectId}/export/evidence-trust-package`);
}

export async function createEvidenceTrustPackage(projectId: string): Promise<EvidenceTrustPackage> {
  return request<EvidenceTrustPackage>(`/api/projects/${projectId}/export/evidence-trust-package`, {
    method: "POST"
  });
}

export async function getAuditLog(projectId: string): Promise<AuditLogEntry[]> {
  return request<AuditLogEntry[]>(`/api/projects/${projectId}/audit`);
}

export async function verifyAuditLog(projectId: string): Promise<AuditVerifyResult> {
  return request<AuditVerifyResult>(`/api/projects/${projectId}/audit/verify`);
}

export async function getIssueResolution(projectId: string): Promise<IssueResolution> {
  return request<IssueResolution>(`/api/projects/${projectId}/review/issue-resolution`);
}

export async function getIssueResolutionReviews(projectId: string): Promise<IssueResolutionReview[]> {
  return request<IssueResolutionReview[]>(`/api/projects/${projectId}/review/issue-resolution/reviews`);
}

export async function recordIssueResolutionReview(
  projectId: string,
  issueId: string,
  payload: IssueResolutionReviewRequest
): Promise<{ review: IssueResolutionReview; issue_resolution: IssueResolution }> {
  return request<{ review: IssueResolutionReview; issue_resolution: IssueResolution }>(
    `/api/projects/${projectId}/review/issue-resolution/${issueId}/review`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function createAuditExport(projectId: string): Promise<AuditExport> {
  return request<AuditExport>(`/api/projects/${projectId}/audit/export`, {
    method: "POST"
  });
}

export async function getAuditExports(projectId: string): Promise<AuditExportSummary[]> {
  return request<AuditExportSummary[]>(`/api/projects/${projectId}/audit/exports`);
}

export async function getAuditExport(
  projectId: string,
  exportId: string
): Promise<AuditExport> {
  return request<AuditExport>(`/api/projects/${projectId}/audit/exports/${exportId}`);
}

export async function getAuditExportReport(
  projectId: string,
  exportId: string
): Promise<AuditExportReport> {
  return request<AuditExportReport>(
    `/api/projects/${projectId}/audit/exports/${exportId}/report`
  );
}

export async function getAuditFileManifest(
  projectId: string,
  exportId: string
): Promise<AuditFileManifest> {
  return request<AuditFileManifest>(
    `/api/projects/${projectId}/audit/exports/${exportId}/manifest`
  );
}

export async function createAuditFilteredExport(
  projectId: string,
  filters: AuditFilteredExportRequest
): Promise<AuditFilteredExport> {
  return request<AuditFilteredExport>(`/api/projects/${projectId}/audit/filtered-export`, {
    method: "POST",
    body: JSON.stringify(filters)
  });
}

export async function getAuditFilteredExports(
  projectId: string
): Promise<AuditFilteredExportSummary[]> {
  return request<AuditFilteredExportSummary[]>(`/api/projects/${projectId}/audit/filtered-exports`);
}

export async function getAuditFilteredExport(
  projectId: string,
  exportId: string
): Promise<AuditFilteredExport> {
  return request<AuditFilteredExport>(
    `/api/projects/${projectId}/audit/filtered-exports/${exportId}`
  );
}

export async function getAuditFilteredExportReport(
  projectId: string,
  exportId: string
): Promise<AuditFilteredExportReport> {
  return request<AuditFilteredExportReport>(
    `/api/projects/${projectId}/audit/filtered-exports/${exportId}/report`
  );
}

export async function getRunHistory(projectId: string): Promise<RunHistory> {
  return request<RunHistory>(`/api/projects/${projectId}/runs`);
}

export async function uploadFile(
  projectId: string,
  kind: "literature" | "data",
  file: File
): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);
  await request(`/api/projects/${projectId}/upload/${kind}`, {
    method: "POST",
    body: formData
  });
}

export const mockOutputs: OutputItem[] = [
  {
    id: "mock-draft",
    agent_name: "Manuscript Agent",
    kind: "manuscript",
    title: "论文 Markdown 初稿",
    relative_path: "manuscript/draft.md",
    mime_type: "text/markdown",
    created_at: new Date().toISOString()
  },
  {
    id: "mock-review",
    agent_name: "Reviewer Agent",
    kind: "review",
    title: "审稿报告 JSON",
    relative_path: "reviews/review_report.json",
    mime_type: "application/json",
    created_at: new Date().toISOString()
  },
  {
    id: "mock-claim-alignment",
    agent_name: "Claim Alignment Agent",
    kind: "provenance",
    title: "Claim 对齐记录",
    relative_path: "provenance/claim_alignment.json",
    mime_type: "application/json",
    created_at: new Date().toISOString()
  },
  {
    id: "mock-analysis-provenance",
    agent_name: "Analysis Agent",
    kind: "analysis",
    title: "分析来源记录",
    relative_path: "analysis/analysis_provenance.json",
    mime_type: "application/json",
    created_at: new Date().toISOString()
  },
  {
    id: "mock-figure",
    agent_name: "Figure Agent",
    kind: "figure",
    title: "图表来源记录",
    relative_path: "figures/figure_provenance.json",
    mime_type: "application/json",
    created_at: new Date().toISOString()
  }
];

export const mockEvidence: EvidenceClaim[] = [
  {
    claim_id: "claim_001",
    section: "Results",
    claim: "The dataset contains 60 samples, 6 columns, and 5 numerical variables.",
    evidence_type: "analysis_summary",
    data_file: "data/demo_data.csv",
    analysis_file: "analysis/result_summary.json",
    analysis_provenance_file: "analysis/analysis_provenance.json",
    figure_file: null,
    figure_provenance_file: null,
    manuscript_file: "manuscript/draft.md",
    evidence_status: "supported",
    human_verified: false
  },
  {
    claim_id: "claim_002",
    section: "Results",
    claim: "Figure 1 summarizes a recorded distribution figure.",
    evidence_type: "figure",
    data_file: "data/demo_data.csv",
    analysis_file: "analysis/result_summary.json",
    analysis_provenance_file: "analysis/analysis_provenance.json",
    figure_file: "figures/figure_1.png",
    figure_provenance_file: "figures/figure_provenance.json",
    manuscript_file: "manuscript/draft.md",
    evidence_status: "supported",
    human_verified: false
  },
  {
    claim_id: "claim_003",
    section: "Results",
    claim: "The Results section is limited to analysis summary and figure provenance records.",
    evidence_type: "manuscript_results",
    data_file: "data/demo_data.csv",
    analysis_file: "analysis/result_summary.json",
    analysis_provenance_file: "analysis/analysis_provenance.json",
    figure_file: "figures/figure_1.png",
    figure_provenance_file: "figures/figure_provenance.json",
    manuscript_file: "manuscript/draft.md",
    evidence_status: "supported",
    human_verified: false
  }
];

export const mockEvidenceClaimReviews: EvidenceClaimReviewsResponse = {
  reviews: [
    {
      review_id: "evidence_claim_review_001",
      claim_id: "claim_001",
      human_status: "supported",
      reason: "Mock human reviewer supports this claim.",
      related_files: ["data/demo_data.csv", "analysis/analysis_provenance.json"],
      created_at: new Date().toISOString(),
      source: "frontend",
      evidence_modified: false
    }
  ],
  summary: {
    generated_at: new Date().toISOString(),
    relative_path: "provenance/evidence_claim_review_summary.json",
    summary: {
      total_claims: 3,
      reviewed: 1,
      supported: 1,
      partially_supported: 0,
      unsupported: 0,
      needs_more_evidence: 0,
      unreviewed: 2
    },
    claims: mockEvidence.map((claim, index) => ({
      claim_id: claim.claim_id,
      section: claim.section,
      claim: claim.claim,
      evidence_type: claim.evidence_type,
      evidence_status: claim.evidence_status,
      latest_human_status: index === 0 ? "supported" : null,
      latest_reason: index === 0 ? "Mock human reviewer supports this claim." : null,
      review_count: index === 0 ? 1 : 0,
      related_files: [
        claim.data_file,
        claim.analysis_file,
        claim.analysis_provenance_file,
        claim.figure_file,
        claim.figure_provenance_file,
        claim.manuscript_file
      ].filter((value): value is string => Boolean(value))
    }))
  }
};

export const mockFigureProvenance: FigureProvenanceRecord[] = [
  {
    figure_id: "fig_001",
    title: "Distribution of temperature",
    figure_type: "histogram",
    source_data: "data/demo_data.csv",
    analysis_file: "analysis/result_summary.json",
    script_or_function: "app.tools.plotting.create_figures",
    output_files: ["figures/figure_1.png", "figures/figure_1.svg"],
    is_ai_generated: false,
    is_experimental_result: true,
    created_at: new Date().toISOString(),
    data_hash: "mock_sha256",
    warnings: []
  }
];

export const mockClaimAlignment: ClaimAlignment = {
  manuscript_file: "manuscript/draft.md",
  evidence_file: "provenance/evidence.json",
  analysis_file: "analysis/result_summary.json",
  figure_provenance_file: "figures/figure_provenance.json",
  alignment_status: "partial",
  aligned_claims: [
    {
      alignment_id: "align_001",
      section: "Results",
      paragraph_index: 1,
      sentence_index: 1,
      sentence: "The analysis summary records 60 rows and 6 columns.",
      matched_claim_id: "claim_001",
      match_status: "matched",
      evidence_status: "supported",
      confidence: "high",
      notes: []
    },
    {
      alignment_id: "align_002",
      section: "Discussion",
      paragraph_index: 1,
      sentence_index: 1,
      sentence: "These patterns suggest a promising direction for future optimization.",
      matched_claim_id: null,
      match_status: "needs_claim_alignment",
      evidence_status: "needs_human_review",
      confidence: "low",
      notes: ["No direct evidence claim found."]
    }
  ],
  summary: {
    total_sentences_checked: 2,
    matched: 1,
    needs_claim_alignment: 1,
    not_claim: 0
  }
};

export const mockSentenceIssues: SentenceIssue[] = [
  {
    issue_id: "sent_issue_001",
    section: "Discussion",
    paragraph_index: 1,
    sentence_index: 1,
    sentence: "These patterns suggest a promising direction for future optimization.",
    issue_type: "discussion_over_inference",
    severity: "major",
    related_claim_id: null,
    evidence_status: "needs_human_review",
    suggested_revision: "Add a supported evidence claim or revise the sentence as limitation.",
    revision_diff: {
      can_auto_suggest: true,
      before: "These patterns suggest a promising direction for future optimization.",
      after:
        "These patterns suggest a promising direction for future optimization. Treat this as a limitation or future-work note unless direct evidence is added.",
      change_type: "mark_as_limitation",
      preserved_claim_id: null,
      preserved_numbers: true,
      preserved_units: true,
      requires_human_approval: true,
      warnings: [
        "Suggestion is not applied to manuscript automatically.",
        "Human approval is required before any manuscript change."
      ]
    }
  }
];

export const mockRevisionDecisions: RevisionDecision[] = [
  {
    decision_id: "rev_decision_0001",
    issue_id: "sent_issue_001",
    decision: "rejected",
    before: mockSentenceIssues[0].revision_diff?.before ?? "",
    after: mockSentenceIssues[0].revision_diff?.after ?? "",
    reason: "Mock reviewer decision.",
    created_at: new Date().toISOString(),
    source: "frontend",
    applied_to_manuscript: false
  }
];

export const mockManuscriptPatches: ManuscriptPatch[] = [
  {
    patch_id: "patch_001",
    source_manuscript: "manuscript/draft.md",
    base_version_id: "v0",
    created_at: new Date().toISOString(),
    status: "proposed",
    source: "accepted_revision_decision",
    items: [
      {
        patch_item_id: "patch_item_001",
        issue_id: mockSentenceIssues[0].issue_id,
        decision_id: "rev_decision_0002",
        section: mockSentenceIssues[0].section,
        paragraph_index: mockSentenceIssues[0].paragraph_index ?? null,
        sentence_index: mockSentenceIssues[0].sentence_index ?? null,
        before: mockSentenceIssues[0].revision_diff?.before ?? "",
        after: mockSentenceIssues[0].revision_diff?.after ?? "",
        change_type: mockSentenceIssues[0].revision_diff?.change_type ?? "mark_as_limitation",
        related_claim_id: mockSentenceIssues[0].related_claim_id,
        evidence_status: mockSentenceIssues[0].evidence_status ?? "needs_human_review",
        requires_human_confirmation: true,
        warnings: mockSentenceIssues[0].revision_diff?.warnings ?? [],
        item_status: "safe",
        manual_edits: [],
        latest_safety_result: {
          safe: true,
          warnings: ["patch item is not linked to a related_claim_id"],
          blocked_reasons: []
        }
      }
    ],
    blocked_items: [],
    summary: {
      total_items: 1,
      safe_to_apply: true,
      requires_human_confirmation: true,
      blocked_items: 0,
      accepted_decisions: 1
    }
  }
];

export const mockManuscriptPatchPreview: ManuscriptPatchPreview = {
  patch_id: "patch_001",
  relative_path: "manuscript/patches/patch_001.preview.md",
  content: `# Manuscript Patch Preview

Patch ID: patch_001
Source manuscript: manuscript/draft.md
Status: proposed

## Patch Item patch_item_001

Section: Discussion
Issue: sent_issue_001
Related claim: -
Change type: mark_as_limitation

### Before

${mockSentenceIssues[0].revision_diff?.before ?? ""}

### After

${mockSentenceIssues[0].revision_diff?.after ?? ""}
`
};

export const mockPatchConflictReport: PatchConflictReport = {
  conflict_report_id: "conflict_001",
  patch_ids: ["patch_001", "patch_002"],
  created_at: new Date().toISOString(),
  relative_path: "manuscript/patches/conflict_report_001.json",
  summary: {
    total_patches: 2,
    total_items: 2,
    conflicts: 1,
    warnings: 0,
    major_conflicts: 1,
    minor_conflicts: 0
  },
  conflicts: [
    {
      conflict_id: "conflict_item_001",
      conflict_type: "same_before_text",
      severity: "major",
      patch_item_refs: [
        {
          patch_id: "patch_001",
          patch_item_id: "patch_item_001",
          issue_id: "sent_issue_001",
          section: "Discussion",
          paragraph_index: 1,
          sentence_index: 1,
          before: mockSentenceIssues[0].revision_diff?.before ?? ""
        }
      ],
      message: "Two patch items share the same before text.",
      resolution_required: true
    }
  ],
  warnings: []
};

export const mockPatchMergePreview: PatchMergePreview = {
  merge_id: "merge_001",
  patch_ids: ["patch_001"],
  created_at: new Date().toISOString(),
  source_manuscript: "manuscript/draft.md",
  status: "preview",
  conflict_report_file: "manuscript/patches/conflict_report_001.json",
  preview_file: "manuscript/patches/merges/merge_001.preview.md",
  can_apply: true,
  confirmed_at: null,
  rejected_at: null,
  generated_version_id: null,
  generated_diff_id: null,
  confirmed_reason: null,
  rejected_reason: null,
  items: [{ patch_id: "patch_001", patch_item_id: "patch_item_001" }],
  blocked_items: [],
  summary: {
    total_items: 1,
    safe_items: 1,
    blocked_items: 0,
    conflicts: 0,
    major_conflicts: 0,
    requires_resolution: false
  }
};

export const mockManuscriptVersionHistory: ManuscriptVersionHistory = {
  versions: [
    {
      version_id: "manuscript_v001",
      file: "manuscript/versions/manuscript_v001.md",
      base_file: "manuscript/draft.md",
      created_at: new Date().toISOString(),
      source_type: "patch",
      source_patch_id: "patch_001",
      source_merge_id: null,
      source_patch_ids: ["patch_001"],
      source_decision_ids: ["rev_decision_0002"],
      source_issue_ids: ["sent_issue_001"],
      status: "created",
      summary: {
        applied_items: 1,
        applied_item_ids: ["patch_item_001"],
        skipped_items: 0,
        skipped_item_details: [],
        warnings: []
      }
    }
  ]
};

export const mockManuscriptVersionContent: ManuscriptVersionContent = {
  version: mockManuscriptVersionHistory.versions[0],
  content:
    "# Title\n\nMock manuscript version.\n\n# Evidence Checklist\n\n- claim_001: supported / analysis_summary\n"
};

export const mockVersionLineage: VersionLineage = {
  generated_at: new Date().toISOString(),
  relative_path: "manuscript/versions/version_lineage.json",
  nodes: [
    { id: "draft", type: "manuscript", label: "draft.md", file: "manuscript/draft.md" },
    { id: "patch_001", type: "patch", label: "patch_001", status: "confirmed" },
    { id: "merge_001", type: "merge", label: "merge_001", status: "preview", can_apply: true },
    { id: "manuscript_v001", type: "version", label: "manuscript_v001", source_type: "patch" },
    { id: "diff_001", type: "diff", label: "diff_001" }
  ],
  edges: [
    { source: "draft", target: "patch_001", relation: "proposed_patch" },
    { source: "patch_001", target: "manuscript_v001", relation: "generated_version" },
    { source: "manuscript_v001", target: "diff_001", relation: "has_diff" }
  ],
  summary: {
    nodes: 5,
    edges: 3,
    versions: 1,
    patches: 1,
    merges: 1,
    diffs: 1
  },
  warnings: []
};

export const mockManuscriptDiffs: ManuscriptDiff[] = [
  {
    diff_id: "diff_001",
    base_file: "manuscript/draft.md",
    version_id: "manuscript_v001",
    version_file: "manuscript/versions/manuscript_v001.md",
    created_at: new Date().toISOString(),
    relative_path: "manuscript/diffs/diff_001.json",
    preview_file: "manuscript/diffs/diff_001.md",
    summary: {
      added_lines: 1,
      removed_lines: 1,
      changed_hunks: 1
    },
    hunks: [
      {
        hunk_id: "hunk_001",
        old_start: 12,
        old_lines: 1,
        new_start: 12,
        new_lines: 1,
        removed: [mockSentenceIssues[0].revision_diff?.before ?? ""],
        added: [mockSentenceIssues[0].revision_diff?.after ?? ""],
        related_issue_ids: ["sent_issue_001"],
        related_claim_ids: []
      }
    ]
  }
];

export const mockManuscriptDiffPreview: ManuscriptDiffPreview = {
  diff_id: "diff_001",
  relative_path: "manuscript/diffs/diff_001.md",
  content:
    "# Manuscript Diff\n\n## hunk_001\n\n- original sentence\n+ revised sentence\n"
};

export const mockRevisionLineDiffs: RevisionLineDiff[] = [
  {
    revision_diff_id: "revision_diff_001",
    base_file: "manuscript/draft.md",
    target_file: "manuscript/versions/manuscript_v001.md",
    created_at: new Date().toISOString(),
    relative_path: "manuscript/revision_diffs/revision_diff_001.json",
    summary: {
      sections_checked: 1,
      paragraphs_checked: 1,
      sentences_changed: 1,
      lines_changed: 1,
      issues_linked: 1,
      claims_linked: 1
    },
    changes: [
      {
        change_id: "change_001",
        section: "Discussion",
        paragraph_index: 1,
        sentence_index: 1,
        line_start: 42,
        line_end: 42,
        before: mockSentenceIssues[0].revision_diff?.before ?? "",
        after: mockSentenceIssues[0].revision_diff?.after ?? "",
        change_type: "mark_as_limitation",
        related_issue_ids: ["sent_issue_001"],
        related_claim_ids: ["claim_001"],
        safety_status: "safe",
        notes: []
      }
    ]
  }
];

export const mockRevisionDiffReviews: RevisionDiffReviewsResponse = {
  reviews: [
    {
      review_id: "rev_diff_review_001",
      revision_diff_id: "revision_diff_001",
      change_id: "change_001",
      human_status: "needs_evidence",
      reason: "Mock reviewer requires evidence confirmation.",
      created_at: new Date().toISOString(),
      source: "frontend"
    }
  ],
  summary: {
    generated_at: new Date().toISOString(),
    relative_path: "manuscript/revision_diffs/revision_diff_review_summary.json",
    summary: {
      total_changes: 1,
      reviewed: 1,
      accepted: 0,
      rejected: 0,
      needs_rewrite: 0,
      needs_evidence: 1,
      unreviewed: 0
    },
    changes: [
      {
        revision_diff_id: "revision_diff_001",
        change_id: "change_001",
        before: mockRevisionLineDiffs[0].changes[0].before,
        after: mockRevisionLineDiffs[0].changes[0].after,
        related_issue_ids: ["sent_issue_001"],
        related_claim_ids: ["claim_001"],
        latest_human_status: "needs_evidence",
        latest_reason: "Mock reviewer requires evidence confirmation.",
        review_count: 1
      }
    ]
  }
};

export const mockIssueResolution: IssueResolution = {
  generated_at: new Date().toISOString(),
  versions: [
    {
      version_id: "manuscript_v001",
      source_type: "patch",
      source_merge_id: null,
      source_patch_ids: ["patch_001"],
      resolved_issue_ids: ["sent_issue_001"],
      unresolved_issue_ids: ["sent_issue_002"],
      partially_resolved_issue_ids: [],
      notes: [],
      human_review_summary: {
        reviewed: 1,
        resolved: 1,
        unresolved: 0,
        needs_review: 0
      },
      latest_human_reviews: [
        {
          review_id: "issue_review_0001",
          issue_id: "sent_issue_001",
          version_id: "manuscript_v001",
          auto_status: "resolved",
          human_status: "resolved",
          reason: "Mock human verification.",
          created_at: new Date().toISOString(),
          source: "frontend"
        }
      ]
    }
  ],
  summary: {
    total_sentence_issues: 2,
    resolved: 1,
    unresolved: 1,
    partially_resolved: 0,
    human_reviews: 1,
    latest_human_status_counts: { resolved: 1 }
  },
  notes: ["Issue resolution is based only on patch/version provenance, not semantic verification."],
  review_history: [
    {
      review_id: "issue_review_0001",
      issue_id: "sent_issue_001",
      version_id: "manuscript_v001",
      auto_status: "resolved",
      human_status: "resolved",
      reason: "Mock human verification.",
      created_at: new Date().toISOString(),
      source: "frontend"
    }
  ]
};

export const mockReviewerClosureSummary: ReviewerClosureSummary = {
  generated_at: new Date().toISOString(),
  relative_path: "reviews/reviewer_closure_summary.json",
  summary: {
    total_sentence_issues: 2,
    closed: 1,
    open: 0,
    unlinked: 1,
    needs_evidence: 0,
    needs_rewrite: 0,
    rejected: 0
  },
  issues: [
    {
      issue_id: "sent_issue_001",
      issue_type: "missing_claim_alignment",
      severity: "major",
      sentence: "The source dataset is data/demo_data.csv.",
      closure_status: "closed",
      linked_changes: [
        {
          revision_diff_id: "revision_diff_001",
          change_id: "change_001",
          before: mockRevisionLineDiffs[0].changes[0].before,
          after: mockRevisionLineDiffs[0].changes[0].after
        }
      ],
      latest_revision_review: mockRevisionDiffReviews.reviews[0],
      reason:
        "Linked revision change was accepted by a human reviewer. This is workflow closure only."
    },
    {
      issue_id: "sent_issue_002",
      issue_type: "missing_claim_alignment",
      severity: "major",
      sentence: "Numerical variables are listed in the draft.",
      closure_status: "unlinked",
      linked_changes: [],
      latest_revision_review: null,
      reason: "No revision diff change is linked to this reviewer issue."
    }
  ],
  notes: [
    "Closed means a linked revision diff change was accepted in this local workflow.",
    "It does not prove the scientific claim or reviewer concern is semantically resolved."
  ]
};

export const mockTrustSummary: TrustSummary = {
  generated_at: new Date().toISOString(),
  relative_path: "trust/trust_summary.json",
  overall_status: "needs_review",
  scores: {
    claim_review_completion: 0.333,
    revision_review_completion: 1,
    reviewer_issue_closure: 0.5,
    pdf_page_review_completion: 1,
    audit_health: 1
  },
  counts: {
    claims_total: 3,
    claims_reviewed: 1,
    claims_unsupported: 0,
    revision_changes_total: 1,
    revision_changes_reviewed: 1,
    metadata_actions_total: 1,
    pdf_pages_reviewed: 1,
    reviewer_issues_total: 2,
    reviewer_issues_open: 1,
    audit_entries: 1,
    failed_runs: 1,
    placeholder_literature_records: 2
  },
  audit_hash_chain: {
    valid: true,
    checked_entries: 1,
    first_invalid_index: null,
    errors: []
  },
  failed_run_diagnostics: [
    {
      run_id: "run_failure_fixture_001",
      failed_step: "analysis",
      likely_cause: "A required local CSV input was missing for the analysis step.",
      suggested_recovery: ["Upload or regenerate the missing CSV file."],
      is_fixture: true
    }
  ],
  open_items: [
    {
      item_type: "literature_metadata",
      item_id: "lit_001",
      status: "placeholder",
      message: "Placeholder or unverified literature metadata prevents ready export."
    }
  ],
  blocking_issues: [
    {
      item_type: "literature_metadata",
      item_id: "lit_001",
      status: "placeholder",
      message: "Placeholder or unverified literature metadata prevents ready export."
    }
  ],
  source_files: {
    evidence_review_summary: "provenance/evidence_claim_review_summary.json",
    revision_diff_review_summary: "manuscript/revision_diffs/revision_diff_review_summary.json",
    metadata_review_summary: "literature/metadata_review_summary.json",
    pdf_page_review_summary: "literature/pdf_page_review_summary.json",
    reviewer_closure_summary: "reviews/reviewer_closure_summary.json",
    audit_log: "audit/audit_log.jsonl",
    run_history: "runs/run_history.json"
  },
  notes: [
    "This dashboard summarizes local workflow trust signals only.",
    "It is not a production compliance, peer review, or scientific truth certificate."
  ]
};

export const mockReadinessReport: ReadinessReport = {
  report_id: "v1_readiness_report",
  generated_at: new Date().toISOString(),
  relative_path: "trust/v1_readiness_report.json",
  readiness_level: "needs_local_review",
  local_mvp_checks: {
    evidence_claim_review_workflow: true,
    trust_summary: true,
    reviewer_closure_summary: true,
    metadata_revert_preview: true,
    pdf_page_text_preview: true,
    analysis_timeline: true,
    run_history_failure_fixture: true,
    audit_hash_chain_valid: true
  },
  trust_overall_status: "needs_review",
  blocking_gaps: ["Placeholder or unverified literature metadata prevents ready export."],
  production_gaps: [
    "No authentication, authorization, role model, or multi-tenant isolation.",
    "No production database, backup, restore, migration, or queue infrastructure.",
    "No real DOI/reference verification service.",
    "No OCR execution or page-level OCR text generation."
  ],
  recommended_next_steps: [
    "Resolve unsupported and unreviewed evidence claims.",
    "Replace placeholder literature metadata with verified references before external use."
  ],
  notes: [
    "v1.0 readiness here means local MVP readiness only.",
    "This report must not be presented as production, compliance, or peer-review readiness."
  ]
};

export const mockProjectExport: ProjectExportInfo = {
  available: true,
  project_id: "demo_project",
  created_at: new Date().toISOString(),
  export_id: "researchagent_demo_project_local_mvp_export_mock",
  file_name: "researchagent_demo_project_local_mvp_export_mock.zip",
  relative_path: "exports/researchagent_demo_project_local_mvp_export_mock.zip",
  size_bytes: 32768,
  included_file_count: 18,
  category_counts: {
    manuscript: 3,
    provenance: 2,
    reviews: 3,
    trust: 2,
    analysis: 3,
    figures: 2,
    literature: 2,
    audit: 1,
    runs: 1
  },
  included_files: [
    { relative_path: "README_EXPORT.md", size_bytes: 900, category: "root" },
    { relative_path: "manuscript/draft.md", size_bytes: 1800, category: "manuscript" },
    { relative_path: "trust/trust_summary.json", size_bytes: 2200, category: "trust" },
    { relative_path: "runs/run_history.json", size_bytes: 1600, category: "runs" }
  ],
  warnings: [],
  excluded_patterns: [".env", ".env.*", "node_modules", ".runtime", "Playwright reports"],
  local_mvp_caveats: [
    "Local MVP export only; not a production backup or compliance archive.",
    "No DOI verification, OCR execution, plagiarism detection, or scientific validity check is performed."
  ]
};

export const mockWorkspaceExport: WorkspaceExportManifest = {
  available: true,
  export_id: "workspace_export_v15",
  project_id: "demo_project",
  generated_at: new Date().toISOString(),
  relative_path: "exports/workspace/workspace_export_manifest.json",
  export_dir: "exports/workspace",
  artifacts: [
    {
      artifact_type: "word_docx",
      relative_path: "exports/workspace/research_workspace_export.docx",
      mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      available: true,
      required: true,
      size_bytes: 16384,
      sha256: "mock_docx_sha256"
    },
    {
      artifact_type: "latex_source",
      relative_path: "exports/workspace/research_workspace_export.tex",
      mime_type: "application/x-tex",
      available: true,
      required: true,
      size_bytes: 4096,
      sha256: "mock_latex_sha256"
    },
    {
      artifact_type: "trust_report_markdown",
      relative_path: "exports/workspace/trust_report.md",
      mime_type: "text/markdown",
      available: true,
      required: true,
      size_bytes: 3072,
      sha256: "mock_trust_md_sha256"
    },
    {
      artifact_type: "trust_report_json",
      relative_path: "exports/workspace/trust_report.json",
      mime_type: "application/json",
      available: true,
      required: true,
      size_bytes: 6144,
      sha256: "mock_trust_json_sha256"
    },
    {
      artifact_type: "workspace_export_manifest",
      relative_path: "exports/workspace/workspace_export_manifest.json",
      mime_type: "application/json",
      available: true,
      required: true,
      size_bytes: 2048,
      sha256: null
    }
  ],
  source_files: [
    { relative_path: "manuscript/draft.md", available: true, size_bytes: 1800 },
    { relative_path: "trust/trust_summary.json", available: true, size_bytes: 2200 },
    { relative_path: "provenance/citation_grounding_report.json", available: true, size_bytes: 1400 },
    { relative_path: "audit/audit_log.jsonl", available: true, size_bytes: 900 }
  ],
  safety: {
    project_relative_paths_only: true,
    secret_scan_passed: true,
    warning_count: 0
  },
  warnings: [],
  caveats: [
    "Workspace export is a local MVP artifact package, not a production backup.",
    "Generated DOCX and LaTeX are drafts for human review.",
    "The trust report is a local workflow summary, not scientific or compliance validation."
  ]
};

export const mockProductionScaffold: ProductionScaffoldReport = {
  version: "v3.0.0-rc1",
  name: "Research Workspace scaffold",
  generated_at: new Date().toISOString(),
  environment: "local",
  status: "scaffold_ready_for_local_validation",
  demo_safe: true,
  mock_fallback: {
    llm_mode: "mock",
    no_api_key_required: true,
    no_external_network_required: true
  },
  capabilities: [
    {
      name: "database",
      mode: "sqlite",
      configured: false,
      fallback: "sqlite",
      notes: ["PostgreSQL is optional and not required for local demo validation."]
    },
    {
      name: "task_queue",
      mode: "inline",
      configured: false,
      fallback: "inline",
      notes: ["Worker scaffold can be smoke-tested without Redis or an external queue."]
    },
    {
      name: "auth",
      mode: "disabled",
      configured: false,
      fallback: "disabled",
      notes: ["Auth scaffold is disabled by default and must be enforced server-side before shared use."]
    },
    {
      name: "containers",
      mode: "docker_compose",
      configured: true,
      fallback: "local_process",
      notes: ["Dockerfiles and compose profiles support repeatable local checks."]
    }
  ],
  worker: {
    mode: "inline",
    concurrency: 1,
    entrypoint: "python -m app.workers.research_worker",
    fallback: "inline"
  },
  deployment_documents: [
    "docs/deployment_v2.md",
    "docs/v2.0_acceptance_criteria.md",
    "docs/v2.0_acceptance_report.md"
  ],
  validation: {
    script: "python scripts/validate_v2.py",
    requires_api_key: false,
    requires_external_network: false
  },
  guardrails: [
    "Do not fabricate DOI, citations, p-values, significance, causal claims, OCR output, or scientific conclusions.",
    "Do not commit secrets, environment files with real values, stack traces, or local absolute paths."
  ],
  blocking_items: [
    "Auth is disabled by default.",
    "PostgreSQL and queue backends are optional scaffolds.",
    "Deployment requires operator review of TLS, backups, monitoring, and rollback steps."
  ]
};

export const mockLiterature: LiteratureRecord[] = [
  {
    literature_id: "lit_001",
    source_file: "literature/demo_literature.md",
    title: "Demo literature placeholder",
    authors: [],
    year: null,
    doi: null,
    journal: null,
    source_type: "markdown",
    parsed_text_file: "literature/demo_literature.md",
    parse_metadata_file: null,
    parse_status: "success",
    metadata_status: "placeholder",
    human_verified: false,
    warnings: [],
    page_count: null,
    empty_page_count: null,
    pages: [],
    quality_score: 1,
    quality_label: "good",
    needs_manual_review: false
  },
  {
    literature_id: "lit_002",
    source_file: "literature/demo_pdf_literature.pdf",
    title: "Demo PDF placeholder",
    authors: [],
    year: null,
    doi: null,
    journal: null,
    source_type: "pdf",
    parsed_text_file: "literature/parsed/demo_pdf_literature.txt",
    parse_metadata_file: "literature/parsed/demo_pdf_literature.metadata.json",
    parse_status: "success",
    metadata_status: "placeholder",
    human_verified: false,
    warnings: ["PyMuPDF unavailable; fallback parser used."],
    page_count: 1,
    empty_page_count: 0,
    pages: [
      {
        page_number: 1,
        char_count: 280,
        empty: false,
        warnings: ["Page-level text split is unavailable in fallback parser."],
        quality_signal: "medium",
        ocr: {
          ocr_attempted: false,
          ocr_engine: null,
          ocr_status: "not_configured",
          ocr_text_file: null
        }
      }
    ],
    quality_score: 0.49,
    quality_label: "medium",
    needs_manual_review: false
  }
];

export const mockLiteratureHistory: LiteratureHistoryEntry[] = [
  {
    history_id: "lit_hist_0001",
    literature_id: "lit_001",
    changed_fields: ["title"],
    old_values: { title: "Demo literature placeholder" },
    new_values: { title: "Demo literature placeholder, manually reviewed" },
    changed_at: new Date().toISOString(),
    source: "api",
    reason: "manual metadata update"
  }
];

export const mockLiteratureMetadataDiff: LiteratureMetadataDiffReport = {
  generated_at: new Date().toISOString(),
  relative_path: "literature/metadata_diff_report.json",
  records: [
    {
      literature_id: "lit_001",
      source_file: "literature/demo_literature.md",
      title: "Demo literature placeholder",
      changes: [
        {
          field: "title",
          old_value: "Demo literature placeholder",
          new_value: "Demo literature placeholder, manually reviewed",
          change_type: "modified",
          source_history_id: "lit_hist_0001",
          revert_suggestion: {
            can_revert: true,
            revert_to: "Demo literature placeholder",
            warning: "Review the source history record before applying this revert manually."
          }
        }
      ],
      summary: {
        added: 0,
        modified: 1,
        removed: 0
      }
    }
  ]
};

export const mockLiteratureMetadataBatch: LiteratureMetadataBatchReview = {
  batch_id: "metadata_batch_001",
  created_at: new Date().toISOString(),
  relative_path: "literature/metadata_review_batch.json",
  source_index: "literature/literature_index.json",
  literature_index_modified: false,
  summary: {
    total_records: 2,
    placeholder: 2,
    extracted: 0,
    verified: 0,
    needs_review: 2
  },
  records: [
    {
      literature_id: "lit_001",
      title: "Demo literature placeholder",
      metadata_status: "placeholder",
      human_verified: false,
      recommended_action: "manual_review_required",
      reasons: ["metadata_status is placeholder"]
    },
    {
      literature_id: "lit_002",
      title: "Demo PDF placeholder",
      metadata_status: "placeholder",
      human_verified: false,
      recommended_action: "manual_review_required",
      reasons: ["metadata_status is placeholder"]
    }
  ]
};

export const mockMetadataReviewActions: MetadataReviewActionsResponse = {
  actions: [
    {
      action_id: "metadata_review_001",
      review_action_id: "metadata_review_001",
      literature_id: "lit_001",
      field: "title",
      action: "needs_verification",
      source_history_id: "lit_hist_0001",
      reason: "Mock reviewer keeps this field in manual verification.",
      created_at: new Date().toISOString(),
      source: "frontend",
      literature_index_modified: false
    }
  ],
  summary: {
    generated_at: new Date().toISOString(),
    relative_path: "literature/metadata_review_summary.json",
    summary: {
      total_actions: 1,
      accept_change: 0,
      reject_change: 0,
      needs_verification: 1,
      request_revert: 0
    },
    records: [
      {
        literature_id: "lit_001",
        field: "title",
        latest_action: "needs_verification",
        review_count: 1,
        latest_reason: "Mock reviewer keeps this field in manual verification.",
        source_history_id: "lit_hist_0001"
      }
    ]
  }
};

export const mockMetadataRevertPreview: MetadataRevertPreview = {
  preview_id: "metadata_revert_preview_001",
  generated_at: new Date().toISOString(),
  relative_path: "literature/metadata_revert_preview_001.json",
  literature_id: "lit_001",
  field: "title",
  source_history_id: "lit_hist_0001",
  current_value: "Demo literature placeholder, manually reviewed",
  revert_to: "Demo literature placeholder",
  history_new_value: "Demo literature placeholder, manually reviewed",
  would_change: true,
  safe_to_apply: true,
  conflicts: [],
  applied: false,
  literature_index_modified: false,
  notes: ["Preview only. No changes were applied to literature_index.json."]
};

export const mockAnalysisProvenance: AnalysisProvenance = {
  analysis_id: "analysis_001",
  input_data_file: "data/demo_data.csv",
  input_data_hash: "mock_sha256",
  analysis_function: "app.tools.csv_profile.profile_csv",
  generated_files: [
    "analysis/result_summary.json",
    "analysis/processed_data.csv",
    "analysis/run_log.txt",
    "analysis/statistical_assistant_report.json",
    "analysis/statistical_assistant_notes.md"
  ],
  parameters: {
    analysis_mode: "descriptive_csv_profile",
    generate_correlation_matrix: true,
    generate_figures: true,
    missing_value_policy: "report_only"
  },
  script_version: {
    analysis_agent: "v0.4",
    csv_profile_tool: "v0.4",
    plotting_tool: "v0.4"
  },
  random_seed: 42,
  random_seed_note: "Used only for generated demo CSV data.",
  output_file_hashes: {
    "analysis/result_summary.json": "mock_summary_sha256",
    "analysis/processed_data.csv": "mock_processed_sha256",
    "analysis/run_log.txt": "mock_log_sha256"
  },
  created_at: new Date().toISOString(),
  runtime: {
    python_version: "3.10.x",
    pandas_version: "2.x",
    numpy_version: "2.x"
  },
  row_count: 60,
  column_count: 6,
  warnings: [],
  limitations: [
    "ResearchAgent v0.4 performs descriptive analysis only.",
    "ResearchAgent v0.4 does not generate p-values or statistical significance claims.",
    "ResearchAgent v0.4 does not perform causal inference."
  ],
  is_demo_data: true
};

export const mockStatisticalAssistantReport: StatisticalAssistantReport = {
  report_id: "statistical_assistant_001",
  generated_at: new Date().toISOString(),
  relative_path: "analysis/statistical_assistant_report.json",
  source_files: {
    summary: "analysis/result_summary.json",
    processed_data: "analysis/processed_data.csv"
  },
  dataset: {
    row_count: 60,
    column_count: 6,
    columns: ["sample_id", "temperature", "concentration", "efficiency", "stability", "band_gap"],
    numeric_columns: ["temperature", "concentration", "efficiency", "stability", "band_gap"],
    categorical_columns: ["sample_id"],
    is_demo_data: true
  },
  data_health: {
    missingness: [
      { column: "sample_id", missing_count: 0, missing_rate: 0, severity: "none" },
      { column: "temperature", missing_count: 0, missing_rate: 0, severity: "none" },
      { column: "concentration", missing_count: 0, missing_rate: 0, severity: "none" },
      { column: "efficiency", missing_count: 0, missing_rate: 0, severity: "none" },
      { column: "stability", missing_count: 0, missing_rate: 0, severity: "none" },
      { column: "band_gap", missing_count: 0, missing_rate: 0, severity: "none" }
    ],
    missing_value_columns: 0,
    constant_columns: [],
    near_constant_columns: [],
    outlier_flags: [
      {
        column: "efficiency",
        method: "iqr_1_5",
        count: 0,
        rate: 0,
        lower_bound: 22.4,
        upper_bound: 32.1
      }
    ],
    outlier_flagged_columns: 0,
    small_sample_warning: false,
    warnings: []
  },
  variable_roles: [
    {
      column: "sample_id",
      dtype: "object",
      role_suggestions: ["id-like", "categorical"],
      reasons: ["Values are mostly unique and should not be treated as a numeric outcome."]
    },
    {
      column: "efficiency",
      dtype: "float64",
      role_suggestions: ["numeric", "outcome-candidate"],
      reasons: ["Name suggests a measured response; human review must confirm the role."]
    },
    {
      column: "temperature",
      dtype: "float64",
      role_suggestions: ["numeric", "predictor-candidate"],
      reasons: ["Numeric process variable candidate; no causal role is inferred."]
    }
  ],
  descriptive_cards: [
    {
      column: "efficiency",
      mean: 26.41,
      std: 1.74,
      min: 22.81,
      max: 30.38,
      missing_count: 0,
      recommended_visualization: "histogram_and_boxplot",
      notes: ["Descriptive card only; no inferential conclusion is generated."]
    },
    {
      column: "temperature",
      mean: 359.1,
      std: 35.0,
      min: 300.9,
      max: 418.2,
      missing_count: 0,
      recommended_visualization: "histogram",
      notes: ["Descriptive card only; no inferential conclusion is generated."]
    }
  ],
  correlation_review: [
    {
      x: "temperature",
      y: "band_gap",
      correlation: 0.99,
      association_strength: "strong_association_candidate",
      recommendation: "Review a scatter plot and source data before making any domain claim.",
      limitations: [
        "Correlation is an association candidate only.",
        "No causal relationship, p-value, or statistical significance is generated."
      ]
    }
  ],
  method_suggestions: [
    {
      method: "descriptive_summary",
      status: "allowed",
      reason: "Summarizes rows, columns, missing values, and numeric distributions.",
      outputs: ["analysis/result_summary.json", "analysis/statistical_assistant_report.json"]
    },
    {
      method: "inferential_statistics",
      status: "blocked_without_human_protocol",
      reason: "v1.4 does not generate p-values or statistical significance claims.",
      outputs: []
    },
    {
      method: "causal_inference",
      status: "blocked",
      reason: "v1.4 does not infer causal relationships from local CSV correlations.",
      outputs: []
    }
  ],
  guardrails: [
    "Use this report as a local descriptive assistant, not as peer-review-ready evidence.",
    "Do not turn association candidates into causal claims.",
    "Do not report p-values or statistical significance from this v1.4 assistant.",
    "Do not treat demo data as real experimental evidence."
  ],
  limitations: [
    "ResearchAgent v1.4 performs descriptive statistical assistance only.",
    "ResearchAgent v1.4 does not generate p-values or statistical significance claims.",
    "ResearchAgent v1.4 does not perform causal inference.",
    "Method and variable-role suggestions require human domain review."
  ]
};

export const mockPDFQualityReport: PDFQualityReport = {
  generated_at: new Date().toISOString(),
  relative_path: "literature/pdf_quality_report.json",
  pdfs: [
    {
      source_file: "literature/demo_pdf_literature.pdf",
      metadata_file: "literature/parsed/demo_pdf_literature.metadata.json",
      quality_label: "medium",
      quality_score: 0.49,
      page_count: 1,
      low_quality_pages: [],
      empty_pages: [],
      suspected_scanned_pages: [],
      issue_categories: {
        low_text: 0,
        empty_page: 0,
        fallback_parser: 1,
        many_warnings: 0,
        ocr_not_configured: 1
      },
      recommended_action: "no_action",
      ocr_attempted: false,
      warnings: ["OCR is not configured; no OCR fallback was executed."]
    }
  ],
  summary: {
    pdf_count: 1,
    low_quality_pdf_count: 0,
    pages_requiring_review: 0
  }
};

export const mockPDFPageReviews: PDFPageReviewsResponse = {
  reviews: [
    {
      review_id: "pdf_page_review_001",
      page_review_id: "pdf_page_review_001",
      source_file: "literature/demo_pdf_literature.pdf",
      page_number: 1,
      auto_quality_signal: "ocr_not_configured",
      human_status: "needs_manual_check",
      reason: "Mock page review requires manual readability confirmation.",
      created_at: new Date().toISOString(),
      source: "frontend",
      ocr_attempted: false
    }
  ],
  summary: {
    generated_at: new Date().toISOString(),
    relative_path: "literature/pdf_page_review_summary.json",
    summary: {
      total_reviews: 1,
      accepted_as_readable: 0,
      needs_ocr: 0,
      ignore_page: 0,
      needs_manual_check: 1
    },
    pages: [
      {
        source_file: "literature/demo_pdf_literature.pdf",
        page_number: 1,
        auto_quality_signal: "ocr_not_configured",
        latest_human_status: "needs_manual_check",
        latest_reason: "Mock page review requires manual readability confirmation.",
        review_count: 1
      }
    ]
  }
};

export const mockPDFPageTextPreview: PDFPageTextPreviewResponse = {
  generated_at: new Date().toISOString(),
  relative_path: "literature/pdf_page_text_previews.json",
  summary: {
    pdf_count: 1,
    page_count: 1,
    ocr_attempted: false
  },
  pages: [
    {
      source_file: "literature/demo_pdf_literature.pdf",
      literature_id: "lit_002",
      page_number: 1,
      char_count: 291,
      text_preview:
        "Demo PDF Literature Placeholder. This parsed text preview comes from existing local parsed text only.",
      parse_status: "available",
      auto_quality_signal: "ocr_not_configured",
      human_status: "needs_manual_check",
      ocr_attempted: false,
      warnings: ["No OCR was attempted for this preview."]
    }
  ],
  notes: ["Preview uses existing parsed text and metadata only. No OCR was attempted."]
};

export const mockLLMStatus: LLMStatus = {
  mode: "mock",
  effective_mode: "mock",
  provider: "openai-compatible",
  model: "gpt-4o-mini",
  base_url_host: "api.openai.com",
  api_key_configured: false,
  timeout_seconds: 20,
  max_retries: 1
};

export const mockLLMTestResult: LLMTestResult = {
  ok: true,
  content: { ok: true, message: "mock LLM test response" },
  raw_content: "{\"ok\":true}",
  mode: "mock",
  provider: "openai-compatible",
  model: "gpt-4o-mini",
  prompt_version: "literature_answer_v1",
  status: "fallback",
  usage: {},
  error: null
};

export const mockPromptRegistry: PromptRegistry = {
  count: 4,
  required_prompt_versions: [
    "literature_answer_v1",
    "citation_support_v1",
    "metadata_extraction_v1",
    "bibtex_generation_v1"
  ],
  prompts: [
    {
      prompt_version: "literature_answer_v1",
      file_name: "literature_answer_v1.md",
      purpose: "Answer with local source passages only.",
      content_sha256: "mock_prompt_hash_1",
      char_count: 320
    },
    {
      prompt_version: "citation_support_v1",
      file_name: "citation_support_v1.md",
      purpose: "Check citation support status.",
      content_sha256: "mock_prompt_hash_2",
      char_count: 280
    },
    {
      prompt_version: "metadata_extraction_v1",
      file_name: "metadata_extraction_v1.md",
      purpose: "Draft metadata candidates.",
      content_sha256: "mock_prompt_hash_3",
      char_count: 260
    },
    {
      prompt_version: "bibtex_generation_v1",
      file_name: "bibtex_generation_v1.md",
      purpose: "Generate verified-only BibTeX drafts.",
      content_sha256: "mock_prompt_hash_4",
      char_count: 260
    }
  ]
};

export const mockLiteratureRAGChunks: LiteratureRAGChunk[] = [
  {
    chunk_id: "chunk_lit_001_0001",
    literature_id: "lit_001",
    source_file: "literature/demo_literature.md",
    parsed_text_file: "literature/demo_literature.md",
    title: "Demo literature placeholder",
    source_type: "markdown",
    metadata_status: "placeholder",
    human_verified: false,
    score: 0.61,
    score_breakdown: {
      keyword_score: 0.72,
      ngram_score: 0.44,
      metadata_trust_score: 0.2,
      quality_score: 0.75
    },
    matched_terms: ["efficiency", "stability"],
    quality_warnings: ["placeholder metadata reduces retrieval trust"],
    start_char: 0,
    end_char: 420,
    text:
      "This placeholder literature mentions process temperature, precursor concentration, efficiency, stability, and band gap.",
    token_count: 8,
    tokens: ["process", "temperature", "efficiency", "stability"],
    chunk_hash: "mock_chunk_hash"
  }
];

export const mockLiteratureRAGAnswers: LiteratureRAGAnswer[] = [
  {
    answer_id: "rag_answer_0001",
    created_at: new Date().toISOString(),
    project_id: "demo_project",
    question: "What does the demo literature mention about efficiency?",
    answer:
      "The local placeholder passage mentions efficiency together with process temperature, precursor concentration, stability, and band gap.",
    answer_support_status: "weakly_supported",
    minimum_support_score: 0.2,
    top_source_score: 0.61,
    source_passage_count: 1,
    source_passages: mockLiteratureRAGChunks,
    unsupported_notes: [],
    limitations: ["Mock fallback; human review is required before citation."],
    retrieval: {
      mode: "local_hybrid",
      retrieval_mode: "local_hybrid",
      top_k: 5,
      returned: 1,
      quality_warnings: ["placeholder metadata reduces retrieval trust"]
    },
    llm: {
      mode: "mock",
      provider: "openai-compatible",
      model: "gpt-4o-mini",
      prompt_version: "literature_answer_v1",
      status: "fallback"
    }
  }
];

export const mockLiteratureRAGIndex: LiteratureRAGIndex = {
  project_id: "demo_project",
  created_at: new Date().toISOString(),
  relative_path: "literature/rag/rag_index.json",
  chunks_file: "literature/rag/chunks.jsonl",
  retrieval_mode: "local_hybrid",
  supported_retrieval_modes: ["local_hybrid", "local_keyword"],
  optional_paperqa2_enabled: false,
  prompt_version: "literature_answer_v1",
  chunk_count: mockLiteratureRAGChunks.length,
  literature_count: 1,
  notes: ["Mock local hybrid RAG index with keyword, n-gram, metadata trust, and chunk quality signals."]
};

export const mockRAGChunkQuality: RAGChunkQualityReport = {
  generated_at: new Date().toISOString(),
  relative_path: "literature/rag/chunk_quality_report.json",
  chunks_file: "literature/rag/chunks.jsonl",
  summary: {
    total_chunks: 1,
    ok: 0,
    needs_review: 1,
    poor: 0,
    placeholder_metadata: 1,
    average_quality_score: 0.75
  },
  items: [
    {
      chunk_id: "chunk_lit_001_0001",
      literature_id: "lit_001",
      source_file: "literature/demo_literature.md",
      title: "Demo literature placeholder",
      metadata_status: "placeholder",
      human_verified: false,
      character_count: 106,
      token_count: 8,
      lexical_diversity: 0.9,
      quality_score: 0.75,
      quality_status: "needs_review",
      warnings: ["placeholder metadata reduces retrieval trust"]
    }
  ],
  limitations: ["Chunk quality is a local heuristic for retrieval review."]
};

export const mockRAGRetrievalEvalSet: RAGRetrievalEvalSet = {
  generated_at: new Date().toISOString(),
  relative_path: "literature/rag/retrieval_eval_set.json",
  retrieval_mode: "local_hybrid",
  cases: [
    {
      case_id: "rag_eval_0001",
      query: "process temperature efficiency stability",
      expected_literature_id: "lit_001",
      expected_chunk_id: "chunk_lit_001_0001",
      source: "local_chunk_tokens",
      notes: ["Local deterministic smoke case."]
    }
  ],
  limitations: ["Eval cases are local smoke checks only."]
};

export const mockRAGRetrievalEvaluation: RAGRetrievalEvalReport = {
  generated_at: new Date().toISOString(),
  relative_path: "literature/rag/retrieval_eval_report.json",
  eval_set_file: "literature/rag/retrieval_eval_set.json",
  retrieval_mode: "local_hybrid",
  metrics: {
    total_cases: 1,
    hit_at_1: 1,
    hit_at_3: 1,
    mean_reciprocal_rank: 1
  },
  results: [
    {
      case_id: "rag_eval_0001",
      query: "process temperature efficiency stability",
      expected_chunk_id: "chunk_lit_001_0001",
      expected_literature_id: "lit_001",
      top_chunk_ids: ["chunk_lit_001_0001"],
      top_literature_ids: ["lit_001"],
      hit_at_1: true,
      hit_at_3: true,
      rank: 1,
      top_score: 0.61,
      top_score_breakdown: {
        keyword_score: 0.72,
        ngram_score: 0.44,
        metadata_trust_score: 0.2,
        quality_score: 0.75
      }
    }
  ],
  limitations: ["Metrics do not prove scientific correctness or production retrieval quality."]
};

export const mockSourcePassageEvidence: SourcePassageEvidenceReport = {
  generated_at: new Date().toISOString(),
  relative_path: "provenance/source_passage_evidence.json",
  source_chunks_file: "literature/rag/chunks.jsonl",
  source_answers_file: "literature/rag/rag_answers.jsonl",
  records: [
    {
      evidence_id: "source_passage_0001",
      answer_id: "rag_answer_0001",
      question: "What does the demo literature mention about efficiency?",
      chunk_id: "chunk_lit_001_0001",
      literature_id: "lit_001",
      source_file: "literature/demo_literature.md",
      title: "Demo literature placeholder",
      metadata_status: "placeholder",
      human_verified: false,
      support_status: "needs_human_review",
      excerpt: mockLiteratureRAGChunks[0].text,
      notes: ["Placeholder metadata requires human review."]
    }
  ],
  summary: { records: 1, supported: 0, partial: 0, needs_human_review: 1 }
};

export const mockMetadataLookupResults: LiteratureMetadataLookupResponse = {
  results: [
    {
      lookup_id: "metadata_lookup_0001",
      created_at: new Date().toISOString(),
      provider: "mock_fixture",
      literature_id: "lit_001",
      source_file: "literature/demo_literature.md",
      query_title: "Demo literature placeholder",
      candidates: [{ title: "Demo literature placeholder", source: "existing_local_metadata" }],
      status: "needs_human_review",
      human_verification_required: true,
      literature_index_modified: false,
      warnings: ["No DOI candidate was supplied by the mock provider."],
      prompt_version: "metadata_extraction_v1"
    }
  ],
  summary: {
    provider: "mock_fixture",
    literature_index_modified: false,
    records: 1,
    needs_human_review: 1
  }
};

export const mockBibTeX: BibTeXResponse = {
  bibtex:
    "% ResearchAgent v1.2 BibTeX draft.\n% Formal entries require metadata_status=verified, human_verified=true, and reference_verification_status=approved.\n% Skipped lit_001: Demo literature placeholder; reference candidate has not been approved and applied. Source: literature/demo_literature.md\n",
  report: {
    generated_at: new Date().toISOString(),
    relative_path: "literature/bibtex_report.json",
    bibtex_file: "literature/references.bib",
    prompt_version: "bibtex_generation_v1",
    formal_entries: 0,
    approved_entries: 0,
    candidate_records: 1,
    rejected_records: 0,
    placeholder_records: 0,
    skipped_records: 1,
    written: [],
    skipped: [
      {
        literature_id: "lit_001",
        title: "Demo literature placeholder",
        metadata_status: "placeholder",
        human_verified: false,
        reference_verification_status: null,
        reason: "reference candidate has not been approved and applied"
      }
    ],
    candidates: [
      {
        literature_id: "lit_001",
        title: "Demo literature placeholder",
        reason: "reference candidate has not been approved and applied"
      }
    ],
    rejected: [],
    placeholders: [],
    warnings: [
      "Formal BibTeX entries are generated only from approved human-verified verified metadata.",
      "Missing fields are not fabricated."
    ]
  }
};

export const mockCitationSupport: CitationSupportReport = {
  generated_at: new Date().toISOString(),
  relative_path: "provenance/citation_support_report.json",
  prompt_version: "citation_support_v1",
  source_chunks_file: "literature/rag/chunks.jsonl",
  source_passage_evidence_file: "provenance/source_passage_evidence.json",
  records: [
    {
      claim_id: "claim_001",
      claim: "The dataset contains descriptive statistics.",
      status: "unsupported",
      matched_chunk_ids: [],
      overlap_terms: 0,
      source_passage_evidence_ids: [],
      notes: ["Local source passages do not prove this claim."]
    }
  ],
  summary: { claims_checked: 1, supported: 0, partial: 0, unsupported: 1, needs_human_review: 0 },
  limitations: ["This report does not verify scientific truth."]
};

export const mockReferenceVerificationResults: ReferenceVerificationResult[] = [
  {
    verification_id: "ref_verify_0001",
    literature_id: "lit_001",
    provider: "mock_fixture",
    query: {
      title: "Demo literature placeholder",
      authors: [],
      year: null,
      doi: null,
      journal: null
    },
    candidate: {
      title: "Demo literature placeholder",
      authors: [],
      year: null,
      doi: null,
      journal: null,
      url: null
    },
    match_scores: {
      title_match_score: 1,
      author_match_score: 0,
      year_match: "missing",
      doi_match: "missing",
      journal_match_score: 0,
      overall_confidence: 0.35
    },
    status: "needs_human_review",
    verification_status: "needs_human_review",
    requires_human_approval: true,
    applied_to_literature_index: false,
    warnings: ["No DOI candidate was supplied; DOI was not fabricated."],
    error: null,
    created_at: new Date().toISOString()
  }
];

export const mockReferenceVerificationSummary: ReferenceVerificationSummaryResponse = {
  generated_at: new Date().toISOString(),
  total: 1,
  total_records: 1,
  summary: {
    total: 1,
    total_records: 1,
    verified_candidate: 0,
    ambiguous_match: 0,
    no_match: 0,
    provider_failed: 0,
    needs_human_review: 1,
    approved: 0,
    rejected: 0
  },
  providers: {
    mock_fixture: 1,
    crossref_optional: 0,
    semantic_scholar_optional: 0,
    pubmed_optional: 0
  }
};

export const mockReferenceApprovals: ReferenceApproval[] = [
  {
    approval_id: "ref_approval_0001",
    verification_id: "ref_verify_0001",
    literature_id: "lit_001",
    decision: "needs_manual_check",
    reason: "Mock candidate requires human review before apply.",
    approved_metadata: {},
    created_at: new Date().toISOString(),
    source: "mock",
    apply_to_literature_index: false,
    applied_to_literature_index: false
  }
];

export const mockReferenceApprovalSummary: ReferenceApprovalSummaryResponse = {
  generated_at: new Date().toISOString(),
  relative_path: "literature/reference_approval_summary.json",
  summary: {
    total_records: 1,
    approved: 0,
    rejected: 0,
    needs_manual_check: 1,
    applied_to_literature_index: 0
  },
  latest_by_literature: {
    lit_001: mockReferenceApprovals[0]
  }
};

export const mockCitationGrounding: CitationGroundingReport = {
  generated_at: new Date().toISOString(),
  relative_path: "provenance/citation_grounding_report.json",
  items: [
    {
      grounding_id: "grounding_0001",
      claim_id: "claim_001",
      claim: "The dataset contains descriptive statistics.",
      candidate_chunk_id: "chunk_lit_001_0001",
      literature_id: "lit_001",
      source_file: "literature/demo_literature.md",
      text_excerpt: "Demo literature placeholder for local citation grounding.",
      grounding_strength: "needs_human_review",
      signals: {
        keyword_overlap: 0.2,
        entity_overlap: 0,
        number_consistency: "not_applicable",
        metadata_verified: false,
        pdf_quality_ok: true,
        llm_assisted: false
      },
      limitations: ["Grounding strength is a heuristic and requires human review."],
      requires_human_review: true
    }
  ],
  summary: { total: 1, strong: 0, moderate: 0, weak: 0, unsupported: 0, needs_human_review: 1 }
};

export const mockManuscriptReferencesStatus: ManuscriptReferencesStatus = {
  generated_at: new Date().toISOString(),
  relative_path: "manuscript/references_status.json",
  preview_file: "manuscript/references_section_preview.md",
  verified_references: [],
  candidate_references: [
    {
      literature_id: "lit_001",
      title: "Demo literature placeholder",
      authors: [],
      year: null,
      doi: null,
      journal: null,
      source_file: "literature/demo_literature.md",
      metadata_status: "placeholder",
      reference_verification_status: null,
      reference_verification_id: null,
      human_verified: false,
      warning: "Candidate reference is not approved and cannot enter formal References.",
      verification_results: mockReferenceVerificationResults
    }
  ],
  placeholder_records: [],
  warnings: ["Candidate references require approval before formal use."]
};

export const mockManuscriptReferencesPreview: ManuscriptReferencesPreview = {
  relative_path: "manuscript/references_section_preview.md",
  content:
    "# References Preview\n\nNo formal References entries are available. Approve and apply references first.\n"
};

export const mockLLMCalls: LLMCallLogEntry[] = [
  {
    call_id: "llm_call_0001",
    created_at: new Date().toISOString(),
    project_id: "demo_project",
    operation: "literature_rag.ask",
    provider: "openai-compatible",
    model: "gpt-4o-mini",
    mode: "mock",
    prompt_version: "literature_answer_v1",
    status: "fallback",
    request_summary: { message_count: 2, char_count: 520, sha256: "mock_request_hash" },
    response_summary: { char_count: 160, sha256: "mock_response_hash", preview: "Mock RAG answer." },
    usage: {
      prompt_tokens: null,
      completion_tokens: null,
      total_tokens: null,
      estimated_cost_usd: null
    },
    error: null,
    attempts: 0,
    metadata: { answer_id: "rag_answer_0001", source_chunk_ids: ["chunk_lit_001_0001"] }
  }
];

export const mockAnalysisComparisons: AnalysisComparison[] = [
  {
    comparison_id: "analysis_compare_001",
    base_provenance: "analysis/analysis_provenance.json",
    target_provenance: "analysis/analysis_provenance.json",
    created_at: new Date().toISOString(),
    relative_path: "analysis/comparisons/analysis_compare_001.json",
    summary: {
      parameters_changed: 0,
      input_hash_changed: false,
      output_hash_changes: 0,
      runtime_changes: 0,
      warnings_changed: 0,
      limitations_changed: 0
    },
    diffs: {
      parameters: [],
      input_data_hash: {
        base: "mock_sha256",
        target: "mock_sha256",
        changed: false
      },
      output_file_hashes: [],
      runtime: [],
      warnings: [],
      limitations: []
    }
  }
];

export const mockAnalysisTimeline: AnalysisTimeline = {
  generated_at: new Date().toISOString(),
  relative_path: "analysis/analysis_timeline.json",
  timeline: [
    {
      timeline_id: "analysis_timeline_001",
      run_id: "run_0001",
      analysis_provenance: "analysis/analysis_provenance.json",
      comparison_ids: ["analysis_compare_001"],
      comparisons: mockAnalysisComparisons,
      created_at: new Date().toISOString(),
      summary: {
        parameters_changed: 0,
        input_hash_changed: false,
        output_hash_changes: 0,
        warnings_changed: 0
      }
    }
  ],
  unlinked_comparisons: [],
  change_summary: {
    runs_total: 2,
    failed_runs: 1,
    comparisons_total: 1,
    comparisons_with_changes: 0,
    parameter_changes_total: 0,
    input_hash_changes_total: 0,
    output_hash_changes_total: 0,
    warning_changes_total: 0
  },
  failed_run_diagnostics: [
    {
      run_id: "run_failure_fixture_001",
      run_type: "step",
      step: "analysis",
      failed_step: "analysis",
      error_type: "missing_input",
      error_message: "data/missing_fixture.csv does not exist.",
      likely_cause: "A required local CSV input was missing for the analysis step.",
      suggested_recovery: ["Upload or regenerate the missing CSV file."],
      recoverable: true,
      retry_hint: "rerun_step",
      is_fixture: true
    }
  ],
  summary: {
    runs: 1,
    comparisons: 1,
    changes_detected: 0,
    failed_runs: 1
  }
};

export const mockAuditLog: AuditLogEntry[] = [
  {
    audit_id: "audit_0001",
    event_type: "run_workflow",
    event_category: "workflow",
    risk_level: "low",
    entity_type: "workflow",
    entity_id: "workflow",
    project_id: "demo_project",
    timestamp: new Date().toISOString(),
    source: "api",
    actor: { type: "local_user", id: "local" },
    summary: "Workflow run completed.",
    details: {
      status: "completed",
      current_step: "completed",
      outputs: ["manuscript/draft.md", "reviews/review_report.json"]
    },
    prev_hash: "GENESIS",
    entry_hash: "mock_entry_hash_0001"
  }
];

export const mockAuditVerify: AuditVerifyResult = {
  valid: true,
  checked_entries: 1,
  first_invalid_index: null,
  errors: []
};

export const mockAuditExports: AuditExportSummary[] = [
  {
    export_id: "audit_export_001",
    created_at: new Date().toISOString(),
    entry_count: 1,
    hash_chain_valid: true,
    source_file: "audit/audit_log.jsonl",
    report_file: "audit/exports/audit_integrity_report_001.md",
    manifest_file: "audit/exports/audit_file_manifest_001.json"
  }
];

export const mockAuditExport: AuditExport = {
  ...mockAuditExports[0],
  first_invalid_index: null,
  entries: mockAuditLog
};

export const mockAuditExportReport: AuditExportReport = {
  export_id: "audit_export_001",
  relative_path: "audit/exports/audit_integrity_report_001.md",
  content:
    "# Audit Integrity Report\n\nHash chain valid: true\n\nThis is a local integrity report, not a production-grade tamper-proof audit system.\n"
};

export const mockAuditFileManifest: AuditFileManifest = {
  manifest_id: "manifest_001",
  project_id: "demo_project",
  export_id: "audit_export_001",
  created_at: new Date().toISOString(),
  relative_path: "audit/exports/audit_file_manifest_001.json",
  file_count: 3,
  category_counts: {
    manuscript: 1,
    review: 1,
    audit: 1
  },
  files: [
    {
      relative_path: "manuscript/draft.md",
      category: "manuscript",
      size_bytes: 1200,
      sha256: "mock_draft_sha256"
    },
    {
      relative_path: "reviews/review_report.json",
      category: "review",
      size_bytes: 800,
      sha256: "mock_review_sha256"
    },
    {
      relative_path: "audit/audit_log.jsonl",
      category: "audit",
      size_bytes: 400,
      sha256: "mock_audit_sha256"
    }
  ],
  warnings: [],
  notes: ["Mock audit manifest for offline dashboard rendering."]
};

export const mockAuditFilteredExports: AuditFilteredExportSummary[] = [
  {
    export_id: "audit_filtered_export_001",
    created_at: new Date().toISOString(),
    source_file: "audit/audit_log.jsonl",
    report_file: "audit/filtered_exports/audit_filtered_report_001.md",
    filters: { risk_level: "low" },
    matching_entry_count: 1
  }
];

export const mockAuditFilteredExport: AuditFilteredExport = {
  ...mockAuditFilteredExports[0],
  entries: mockAuditLog,
  warnings: []
};

export const mockAuditFilteredExportReport: AuditFilteredExportReport = {
  export_id: "audit_filtered_export_001",
  relative_path: "audit/filtered_exports/audit_filtered_report_001.md",
  content:
    "# Filtered Audit Report\n\nFilters: `{ \"risk_level\": \"low\" }`\n\n- `audit_0001` `workflow` `low`: Workflow run completed.\n"
};

export const mockRunHistory: RunHistory = {
  runs: [
    {
      run_id: "run_0001",
      run_type: "workflow",
      step: null,
      status: "completed",
      start_time: new Date().toISOString(),
      end_time: new Date().toISOString(),
      duration_seconds: 1.2,
      outputs: ["manuscript/draft.md", "reviews/review_report.json"],
      errors: [],
      warnings: [],
      failure_diagnostics: {
        error_type: null,
        error_message: null,
        failed_step: null,
        likely_cause: null,
        suggested_recovery: []
      },
      recoverable: true,
      retry_hint: null
    },
    {
      run_id: "run_failure_fixture_001",
      run_type: "step",
      step: "analysis",
      status: "failed",
      start_time: new Date().toISOString(),
      end_time: new Date().toISOString(),
      duration_seconds: 2,
      outputs: [],
      errors: ["Fixture failure: missing input file data/missing_fixture.csv."],
      warnings: ["This failed run is an explicit v0.10 fixture."],
      failure_diagnostics: {
        error_type: "missing_input",
        error_message: "data/missing_fixture.csv does not exist.",
        failed_step: "analysis",
        likely_cause: "A required local CSV input was missing for the analysis step.",
        suggested_recovery: ["Upload or regenerate the missing CSV file."]
      },
      recoverable: true,
      retry_hint: "rerun_step",
      is_fixture: true
    }
  ]
};

export function mockOutputContent(output: OutputItem): OutputContent {
  if (output.relative_path.endsWith(".json")) {
    let content: OutputContent["content"] = mockEvidence;
    if (output.relative_path.includes("figure_provenance")) content = mockFigureProvenance;
    if (output.relative_path.includes("claim_alignment")) content = mockClaimAlignment;
    if (output.relative_path.includes("analysis_provenance")) content = mockAnalysisProvenance;
    if (output.relative_path.includes("review_report")) {
      content = {
        overall_decision: "major_revision",
        sentence_issues: mockSentenceIssues,
        citation_issues: ["Placeholder literature metadata remains."]
      };
    }
    return {
      id: output.id,
      title: output.title,
      relative_path: output.relative_path,
      mime_type: output.mime_type,
      content,
      binary: false
    };
  }
  return {
    id: output.id,
    title: output.title,
    relative_path: output.relative_path,
    mime_type: output.mime_type,
    content:
      "# Title\n\nMock manuscript preview.\n\n# Evidence Checklist\n\n- claim_001: supported / analysis_summary",
    binary: false
  };
}

export const mockProject: ProjectDetail = {
  id: "demo_project",
  name: "新型钙钛矿材料研究",
  domain: "materials",
  language: "zh",
  output_format: "markdown",
  workflow_status: "completed",
  current_step: "completed",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  resources: {
    literature_count: 2,
    dataset_count: 1,
    figure_count: 2,
    manuscript_count: 2,
    review_count: 2
  },
  latest_outputs: mockOutputs
};
