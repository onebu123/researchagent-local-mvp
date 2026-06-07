"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpenCheck,
  Bot,
  BrainCircuit,
  ClipboardCheck,
  Database,
  FileArchive,
  FileCheck2,
  FileText,
  FlaskConical,
  GitCompareArrows,
  GitBranch,
  History,
  LineChart,
  Link2,
  PenLine,
  ScrollText,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  TerminalSquare
} from "lucide-react";
import { AgentCard } from "@/components/AgentCard";
import { AuditExportPanel } from "@/components/AuditExportPanel";
import { AuditFilterExportPanel } from "@/components/AuditFilterExportPanel";
import { AnalysisComparePanel } from "@/components/AnalysisComparePanel";
import { AnalysisTimelinePanel } from "@/components/AnalysisTimelinePanel";
import { AnalysisProvenancePanel } from "@/components/AnalysisProvenancePanel";
import { AuditLogPanel } from "@/components/AuditLogPanel";
import { AuditVerifyPanel } from "@/components/AuditVerifyPanel";
import { ClaimAlignmentPanel } from "@/components/ClaimAlignmentPanel";
import { EvidenceClaimReviewPanel } from "@/components/EvidenceClaimReviewPanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { FigureProvenancePanel } from "@/components/FigureProvenancePanel";
import { GlobalTrustDashboard } from "@/components/GlobalTrustDashboard";
import { IssueResolutionPanel } from "@/components/IssueResolutionPanel";
import { BibTeXPanel } from "@/components/BibTeXPanel";
import { CitationSupportPanel } from "@/components/CitationSupportPanel";
import { CitationGroundingPanel } from "@/components/CitationGroundingPanel";
import { LLMCallLogPanel } from "@/components/LLMCallLogPanel";
import { LLMSettingsPanel } from "@/components/LLMSettingsPanel";
import { LiteratureHistoryPanel } from "@/components/LiteratureHistoryPanel";
import { LiteratureMetadataBatchPanel } from "@/components/LiteratureMetadataBatchPanel";
import { LiteratureMetadataDiffPanel } from "@/components/LiteratureMetadataDiffPanel";
import { LiteratureMetadataPanel } from "@/components/LiteratureMetadataPanel";
import { LiteratureMetadataLookupPanel } from "@/components/LiteratureMetadataLookupPanel";
import { LiteratureRAGPanel } from "@/components/LiteratureRAGPanel";
import { LocalMVPOverviewPanel } from "@/components/LocalMVPOverviewPanel";
import { ManuscriptDiffPanel } from "@/components/ManuscriptDiffPanel";
import { ManuscriptPatchPanel } from "@/components/ManuscriptPatchPanel";
import { ManuscriptVersionPanel } from "@/components/ManuscriptVersionPanel";
import { Notifications } from "@/components/Notifications";
import { OutputDetailDrawer } from "@/components/OutputDetailDrawer";
import { PDFQualityPanel } from "@/components/PDFQualityPanel";
import { PDFQualityReportPanel } from "@/components/PDFQualityReportPanel";
import { PDFPageReviewPanel } from "@/components/PDFPageReviewPanel";
import { PatchConflictPanel } from "@/components/PatchConflictPanel";
import { PatchItemEditorPanel } from "@/components/PatchItemEditorPanel";
import { PatchMergePanel } from "@/components/PatchMergePanel";
import { ProgressPanel } from "@/components/ProgressPanel";
import { ProjectExportPanel } from "@/components/ProjectExportPanel";
import { RAGQualityPanel } from "@/components/RAGQualityPanel";
import { RecentOutputs } from "@/components/RecentOutputs";
import { ResourcePanel } from "@/components/ResourcePanel";
import { RevisionDiffPanel } from "@/components/RevisionDiffPanel";
import { RevisionDiffReviewPanel } from "@/components/RevisionDiffReviewPanel";
import { RevisionLineDiffPanel } from "@/components/RevisionLineDiffPanel";
import { MetadataRevertPreviewPanel } from "@/components/MetadataRevertPreviewPanel";
import { MetadataReviewWorkflowPanel } from "@/components/MetadataReviewWorkflowPanel";
import { PDFPageTextPreviewPanel } from "@/components/PDFPageTextPreviewPanel";
import { ReadinessReportPanel } from "@/components/ReadinessReportPanel";
import { ReleaseReadinessPanel } from "@/components/ReleaseReadinessPanel";
import { ReviewerClosurePanel } from "@/components/ReviewerClosurePanel";
import { RunHistoryPanel } from "@/components/RunHistoryPanel";
import { SentenceIssuesPanel } from "@/components/SentenceIssuesPanel";
import { Sidebar } from "@/components/Sidebar";
import { SourcePassageEvidencePanel } from "@/components/SourcePassageEvidencePanel";
import { StatisticalAssistantPanel } from "@/components/StatisticalAssistantPanel";
import { ReferenceApprovalPanel } from "@/components/ReferenceApprovalPanel";
import { ReferenceVerificationPanel } from "@/components/ReferenceVerificationPanel";
import { StatCard } from "@/components/StatCard";
import { TaskCenter } from "@/components/TaskCenter";
import { Topbar } from "@/components/Topbar";
import { UploadPanel } from "@/components/UploadPanel";
import { VersionLineagePanel } from "@/components/VersionLineagePanel";
import { VerifiedReferencesPanel } from "@/components/VerifiedReferencesPanel";
import { WorkflowTimeline } from "@/components/WorkflowTimeline";
import {
  getAnalysisProvenance,
  generateStatisticalAssistant,
  generateAnalysisComparison,
  generateLiteratureMetadataBatchReview,
  generateRevisionLineDiff,
  getAuditLog,
  createProjectExport,
  createAuditFilteredExport,
  getAuditExport,
  getAuditFilteredExport,
  getAuditFilteredExportReport,
  getAuditFilteredExports,
  getAuditFileManifest,
  getAuditExportReport,
  getAuditExports,
  getEnhancedAnalysisTimeline,
  getClaimAlignment,
  getEvidence,
  getEvidenceClaimReviews,
  getFigureProvenance,
  getIssueResolution,
  getLiterature,
  getLiteratureHistory,
  getLiteratureMetadataDiff,
  getManuscriptDiff,
  getManuscriptDiffPreview,
  getManuscriptDiffs,
  getManuscriptPatch,
  getManuscriptPatches,
  getManuscriptPatchPreview,
  getManuscriptVersion,
  getManuscriptVersions,
  getOutput,
  getProject,
  getProjectExport,
  getLLMCalls,
  getLLMStatus,
  getPromptRegistry,
  getLiteratureRAGAnswers,
  getLiteratureRAGChunks,
  getRAGChunkQuality,
  getRAGRetrievalEvalSet,
  getRAGRetrievalEvaluation,
  evaluateRAGRetrieval,
  getSourcePassageEvidence,
  getMetadataLookupResults,
  getBibTeX,
  getCitationSupport,
  getCitationGrounding,
  getManuscriptReferencesPreview,
  getManuscriptReferencesStatus,
  getPDFQualityReport,
  getPDFPageReviews,
  getPDFPageTextPreview,
  getRevisionDecisions,
  getRevisionDiffReviews,
  getRevisionLineDiff,
  getRevisionLineDiffs,
  getReadinessReport,
  getReviewerClosureSummary,
  getRunHistory,
  getSentenceIssues,
  getStatisticalAssistant,
  getTrustSummary,
  checkPatchConflicts,
  confirmPatchMerge,
  generateManuscriptPatch,
  generateBibTeX,
  getReferenceApprovals,
  getReferenceApprovalSummary,
  getReferenceVerificationResults,
  getReferenceVerificationSummary,
  buildLiteratureRAG,
  askLiteratureRAG,
  generateManuscriptDiff,
  generatePatchMergePreview,
  listProjects,
  confirmManuscriptPatch,
  createAuditExport,
  createRevisionDecision,
  editManuscriptPatchItem,
  previewMetadataRevert,
  getVersionLineage,
  mockAnalysisProvenance,
  mockStatisticalAssistantReport,
  mockAnalysisComparisons,
  mockAnalysisTimeline,
  mockAuditExport,
  mockAuditFilteredExport,
  mockAuditFilteredExportReport,
  mockAuditFilteredExports,
  mockAuditFileManifest,
  mockAuditExportReport,
  mockAuditExports,
  mockAuditLog,
  mockAuditVerify,
  mockClaimAlignment,
  mockEvidence,
  mockEvidenceClaimReviews,
  mockFigureProvenance,
  mockMetadataRevertPreview,
  mockPDFPageTextPreview,
  mockProjectExport,
  mockReadinessReport,
  mockReviewerClosureSummary,
  mockIssueResolution,
  mockBibTeX,
  mockCitationSupport,
  mockCitationGrounding,
  mockLLMCalls,
  mockLLMStatus,
  mockLLMTestResult,
  mockLiterature,
  mockLiteratureRAGAnswers,
  mockLiteratureRAGChunks,
  mockLiteratureRAGIndex,
  mockRAGChunkQuality,
  mockRAGRetrievalEvalSet,
  mockRAGRetrievalEvaluation,
  mockLiteratureHistory,
  mockMetadataLookupResults,
  mockManuscriptReferencesPreview,
  mockManuscriptReferencesStatus,
  mockLiteratureMetadataBatch,
  mockLiteratureMetadataDiff,
  mockMetadataReviewActions,
  mockManuscriptDiffPreview,
  mockManuscriptDiffs,
  mockManuscriptPatches,
  mockManuscriptPatchPreview,
  mockManuscriptVersionContent,
  mockManuscriptVersionHistory,
  mockOutputContent,
  mockProject,
  mockRevisionDecisions,
  mockRevisionDiffReviews,
  mockRevisionLineDiffs,
  mockRunHistory,
  mockTrustSummary,
  mockSentenceIssues,
  mockPatchConflictReport,
  mockPatchMergePreview,
  mockPromptRegistry,
  mockReferenceApprovals,
  mockReferenceApprovalSummary,
  mockReferenceVerificationResults,
  mockReferenceVerificationSummary,
  mockSourcePassageEvidence,
  mockVersionLineage,
  patchLiterature,
  reviewEvidenceClaim,
  reviewMetadataChange,
  reviewPDFPage,
  reviewRevisionDiffChange,
  recordIssueResolutionReview,
  runWorkflow,
  approveReferenceVerification,
  runReferenceVerification,
  runMetadataLookup,
  safetyCheckManuscriptPatchItem,
  testLLM,
  uploadFile,
  suggestLiteratureMetadataRevert,
  verifyAuditLog,
  getAnalysisComparison,
  getAnalysisComparisons,
  mockPDFPageReviews,
  mockPDFQualityReport,
  getMetadataReviewActions
} from "@/lib/api";
import type {
  AnalysisComparison,
  AnalysisProvenance,
  AnalysisTimeline,
  AuditExport,
  AuditFilteredExport,
  AuditFilteredExportReport,
  AuditFilteredExportSummary,
  AuditFileManifest,
  AuditExportReport,
  AuditExportSummary,
  AuditLogEntry,
  AuditVerifyResult,
  BibTeXResponse,
  CitationGroundingReport,
  CitationSupportReport,
  ClaimAlignment,
  EvidenceClaim,
  EvidenceClaimReviewStatus,
  EvidenceClaimReviewsResponse,
  FigureProvenanceRecord,
  IssueResolution,
  LLMCallLogEntry,
  LLMStatus,
  LLMTestResult,
  LiteratureHistoryEntry,
  LiteratureMetadataLookupResponse,
  LiteratureMetadataBatchReview,
  LiteratureMetadataDiffReport,
  LiteratureMetadataRevertSuggestion,
  LiteraturePatch,
  LiteratureRAGAnswer,
  LiteratureRAGChunk,
  LiteratureRAGIndex,
  RAGChunkQualityReport,
  RAGRetrievalEvalReport,
  RAGRetrievalEvalSet,
  LiteratureRecord,
  MetadataRevertPreview,
  MetadataReviewActionValue,
  MetadataReviewActionsResponse,
  ManuscriptDiff,
  ManuscriptDiffPreview,
  ManuscriptPatch,
  ManuscriptPatchItem,
  ManuscriptPatchPreview,
  ManuscriptReferencesPreview,
  ManuscriptReferencesStatus,
  ManuscriptVersionContent,
  ManuscriptVersionHistory,
  OutputContent,
  OutputItem,
  ProjectDetail,
  ProjectExportInfo,
  ReferenceApproval,
  ReferenceApprovalDecision,
  ReferenceApprovalSummaryResponse,
  ReferenceVerificationProvider,
  ReferenceVerificationResult,
  ReferenceVerificationSummaryResponse,
  PDFQualityReport,
  PDFPageReviewsResponse,
  PDFPageTextPreviewResponse,
  PromptRegistry,
  ReadinessReport,
  RevisionDecision,
  RevisionDiffHumanStatus,
  RevisionDiffReviewsResponse,
  ReviewerClosureSummary,
  RevisionLineDiff,
  RunHistory,
  SentenceIssue,
  SourcePassageEvidenceReport,
  StatisticalAssistantReport,
  PatchConflictReport,
  PatchMergePreview,
  TrustSummary,
  VersionLineage
} from "@/lib/types";

const workflowOrder = [
  "literature",
  "topic",
  "analysis",
  "figure",
  "provenance",
  "manuscript",
  "claim_alignment",
  "refinement",
  "reviewer"
];

const quickActions = [
  { label: "文献检索", icon: SearchCheck },
  { label: "数据分析", icon: BarChart3 },
  { label: "实验设计", icon: FlaskConical },
  { label: "论文撰写", icon: FileText }
];

type DetailMode =
  | "none"
  | "output"
  | "evidence"
  | "evidenceClaimReview"
  | "figures"
  | "globalTrust"
  | "claimAlignment"
  | "sentenceIssues"
  | "literature"
  | "llmSettings"
  | "llmCallLog"
  | "literatureRag"
  | "ragQuality"
  | "sourcePassageEvidence"
  | "literatureMetadataLookup"
  | "referenceVerification"
  | "referenceApproval"
  | "verifiedReferences"
  | "citationGrounding"
  | "bibtex"
  | "citationSupport"
  | "analysisProvenance"
  | "statisticalAssistant"
  | "revisionDiff"
  | "revisionLineDiff"
  | "literatureHistory"
  | "literatureMetadataDiff"
  | "literatureMetadataBatch"
  | "pdfQuality"
  | "pdfQualityReport"
  | "analysisCompare"
  | "analysisTimeline"
  | "reviewerClosure"
  | "auditLog"
  | "auditVerify"
  | "revisionDiffReview"
  | "metadataReviewWorkflow"
  | "metadataRevertPreview"
  | "pdfPageReview"
  | "pdfPageTextPreview"
  | "auditFilterExport"
  | "manuscriptPatch"
  | "manuscriptVersions"
  | "runHistory"
  | "patchItemEditor"
  | "patchConflicts"
  | "patchMerge"
  | "manuscriptDiff"
  | "versionLineage"
  | "issueResolution"
  | "readinessReport"
  | "releaseReadiness"
  | "projectExport"
  | "auditExport";

export default function DashboardPage() {
  const [project, setProject] = useState<ProjectDetail>(mockProject);
  const [apiOnline, setApiOnline] = useState(false);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string>();
  const [detailMode, setDetailMode] = useState<DetailMode>("none");
  const [selectedOutput, setSelectedOutput] = useState<OutputItem>();
  const [outputContent, setOutputContent] = useState<OutputContent>();
  const [evidence, setEvidence] = useState<EvidenceClaim[]>(mockEvidence);
  const [evidenceClaimReviews, setEvidenceClaimReviews] =
    useState<EvidenceClaimReviewsResponse>(mockEvidenceClaimReviews);
  const [figureProvenance, setFigureProvenance] =
    useState<FigureProvenanceRecord[]>(mockFigureProvenance);
  const [trustSummary, setTrustSummary] = useState<TrustSummary>(mockTrustSummary);
  const [reviewerClosure, setReviewerClosure] =
    useState<ReviewerClosureSummary>(mockReviewerClosureSummary);
  const [claimAlignment, setClaimAlignment] = useState<ClaimAlignment>(mockClaimAlignment);
  const [sentenceIssues, setSentenceIssues] = useState<SentenceIssue[]>(mockSentenceIssues);
  const [literature, setLiterature] = useState<LiteratureRecord[]>(mockLiterature);
  const [llmStatus, setLLMStatus] = useState<LLMStatus>(mockLLMStatus);
  const [llmTestResult, setLLMTestResult] = useState<LLMTestResult | undefined>(mockLLMTestResult);
  const [promptRegistry, setPromptRegistry] = useState<PromptRegistry>(mockPromptRegistry);
  const [llmCalls, setLLMCalls] = useState<LLMCallLogEntry[]>(mockLLMCalls);
  const [literatureRagIndex, setLiteratureRagIndex] =
    useState<LiteratureRAGIndex | undefined>(mockLiteratureRAGIndex);
  const [literatureRagChunks, setLiteratureRagChunks] =
    useState<LiteratureRAGChunk[]>(mockLiteratureRAGChunks);
  const [literatureRagAnswers, setLiteratureRagAnswers] =
    useState<LiteratureRAGAnswer[]>(mockLiteratureRAGAnswers);
  const [ragChunkQuality, setRAGChunkQuality] =
    useState<RAGChunkQualityReport>(mockRAGChunkQuality);
  const [ragRetrievalEvalSet, setRAGRetrievalEvalSet] =
    useState<RAGRetrievalEvalSet>(mockRAGRetrievalEvalSet);
  const [ragRetrievalEvaluation, setRAGRetrievalEvaluation] =
    useState<RAGRetrievalEvalReport>(mockRAGRetrievalEvaluation);
  const [sourcePassageEvidence, setSourcePassageEvidence] =
    useState<SourcePassageEvidenceReport>(mockSourcePassageEvidence);
  const [metadataLookupProvider, setMetadataLookupProvider] = useState("mock_fixture");
  const [metadataLookupResults, setMetadataLookupResults] =
    useState<LiteratureMetadataLookupResponse>(mockMetadataLookupResults);
  const [bibtex, setBibtex] = useState<BibTeXResponse>(mockBibTeX);
  const [citationSupport, setCitationSupport] =
    useState<CitationSupportReport>(mockCitationSupport);
  const [referenceVerificationProvider, setReferenceVerificationProvider] =
    useState<ReferenceVerificationProvider>("mock_fixture");
  const [referenceVerificationResults, setReferenceVerificationResults] =
    useState<ReferenceVerificationResult[]>(mockReferenceVerificationResults);
  const [referenceVerificationSummary, setReferenceVerificationSummary] =
    useState<ReferenceVerificationSummaryResponse>(mockReferenceVerificationSummary);
  const [referenceApprovals, setReferenceApprovals] =
    useState<ReferenceApproval[]>(mockReferenceApprovals);
  const [referenceApprovalSummary, setReferenceApprovalSummary] =
    useState<ReferenceApprovalSummaryResponse>(mockReferenceApprovalSummary);
  const [citationGrounding, setCitationGrounding] =
    useState<CitationGroundingReport>(mockCitationGrounding);
  const [manuscriptReferencesStatus, setManuscriptReferencesStatus] =
    useState<ManuscriptReferencesStatus>(mockManuscriptReferencesStatus);
  const [manuscriptReferencesPreview, setManuscriptReferencesPreview] =
    useState<ManuscriptReferencesPreview>(mockManuscriptReferencesPreview);
  const [analysisProvenance, setAnalysisProvenance] =
    useState<AnalysisProvenance>(mockAnalysisProvenance);
  const [statisticalAssistant, setStatisticalAssistant] =
    useState<StatisticalAssistantReport>(mockStatisticalAssistantReport);
  const [revisionDecisions, setRevisionDecisions] =
    useState<RevisionDecision[]>(mockRevisionDecisions);
  const [manuscriptPatches, setManuscriptPatches] =
    useState<ManuscriptPatch[]>(mockManuscriptPatches);
  const [selectedPatch, setSelectedPatch] = useState<ManuscriptPatch | undefined>(
    mockManuscriptPatches[0]
  );
  const [selectedPatchItem, setSelectedPatchItem] =
    useState<ManuscriptPatchItem | undefined>(mockManuscriptPatches[0]?.items[0]);
  const [patchPreview, setPatchPreview] =
    useState<ManuscriptPatchPreview | undefined>(mockManuscriptPatchPreview);
  const [patchConflictReport, setPatchConflictReport] =
    useState<PatchConflictReport | undefined>(mockPatchConflictReport);
  const [patchMergePreview, setPatchMergePreview] =
    useState<PatchMergePreview | undefined>(mockPatchMergePreview);
  const [manuscriptVersions, setManuscriptVersions] =
    useState<ManuscriptVersionHistory>(mockManuscriptVersionHistory);
  const [selectedVersion, setSelectedVersion] =
    useState<ManuscriptVersionContent | undefined>(mockManuscriptVersionContent);
  const [manuscriptDiffs, setManuscriptDiffs] =
    useState<ManuscriptDiff[]>(mockManuscriptDiffs);
  const [selectedManuscriptDiff, setSelectedManuscriptDiff] =
    useState<ManuscriptDiff | undefined>(mockManuscriptDiffs[0]);
  const [manuscriptDiffPreview, setManuscriptDiffPreview] =
    useState<ManuscriptDiffPreview | undefined>(mockManuscriptDiffPreview);
  const [revisionLineDiffs, setRevisionLineDiffs] =
    useState<RevisionLineDiff[]>(mockRevisionLineDiffs);
  const [selectedRevisionLineDiff, setSelectedRevisionLineDiff] =
    useState<RevisionLineDiff | undefined>(mockRevisionLineDiffs[0]);
  const [revisionDiffReviews, setRevisionDiffReviews] =
    useState<RevisionDiffReviewsResponse>(mockRevisionDiffReviews);
  const [versionLineage, setVersionLineage] = useState<VersionLineage>(mockVersionLineage);
  const [literatureHistory, setLiteratureHistory] =
    useState<LiteratureHistoryEntry[]>(mockLiteratureHistory);
  const [literatureMetadataDiff, setLiteratureMetadataDiff] =
    useState<LiteratureMetadataDiffReport>(mockLiteratureMetadataDiff);
  const [literatureMetadataRevertSuggestion, setLiteratureMetadataRevertSuggestion] =
    useState<LiteratureMetadataRevertSuggestion | undefined>();
  const [metadataRevertPreview, setMetadataRevertPreview] =
    useState<MetadataRevertPreview | undefined>(mockMetadataRevertPreview);
  const [literatureMetadataBatch, setLiteratureMetadataBatch] =
    useState<LiteratureMetadataBatchReview>(mockLiteratureMetadataBatch);
  const [metadataReviewActions, setMetadataReviewActions] =
    useState<MetadataReviewActionsResponse>(mockMetadataReviewActions);
  const [pdfQualityReport, setPDFQualityReport] =
    useState<PDFQualityReport>(mockPDFQualityReport);
  const [pdfPageReviews, setPDFPageReviews] =
    useState<PDFPageReviewsResponse>(mockPDFPageReviews);
  const [pdfPageTextPreview, setPDFPageTextPreview] =
    useState<PDFPageTextPreviewResponse>(mockPDFPageTextPreview);
  const [analysisComparisons, setAnalysisComparisons] =
    useState<AnalysisComparison[]>(mockAnalysisComparisons);
  const [selectedAnalysisComparison, setSelectedAnalysisComparison] =
    useState<AnalysisComparison | undefined>(mockAnalysisComparisons[0]);
  const [analysisTimeline, setAnalysisTimeline] =
    useState<AnalysisTimeline>(mockAnalysisTimeline);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>(mockAuditLog);
  const [auditVerify, setAuditVerify] = useState<AuditVerifyResult>(mockAuditVerify);
  const [issueResolution, setIssueResolution] =
    useState<IssueResolution>(mockIssueResolution);
  const [auditExports, setAuditExports] = useState<AuditExportSummary[]>(mockAuditExports);
  const [selectedAuditExport, setSelectedAuditExport] =
    useState<AuditExport | undefined>(mockAuditExport);
  const [auditExportReport, setAuditExportReport] =
    useState<AuditExportReport | undefined>(mockAuditExportReport);
  const [auditFileManifest, setAuditFileManifest] =
    useState<AuditFileManifest | undefined>(mockAuditFileManifest);
  const [auditFilteredExports, setAuditFilteredExports] =
    useState<AuditFilteredExportSummary[]>(mockAuditFilteredExports);
  const [selectedAuditFilteredExport, setSelectedAuditFilteredExport] =
    useState<AuditFilteredExport | undefined>(mockAuditFilteredExport);
  const [auditFilteredExportReport, setAuditFilteredExportReport] =
    useState<AuditFilteredExportReport | undefined>(mockAuditFilteredExportReport);
  const [auditFilterRiskLevel, setAuditFilterRiskLevel] = useState("low");
  const [runHistory, setRunHistory] = useState<RunHistory>(mockRunHistory);
  const [readinessReport, setReadinessReport] = useState<ReadinessReport>(mockReadinessReport);
  const [projectExport, setProjectExport] = useState<ProjectExportInfo>(mockProjectExport);
  const [detailLoading, setDetailLoading] = useState(false);
  const [decisionLoadingId, setDecisionLoadingId] = useState<string | null>(null);
  const [issueReviewLoadingId, setIssueReviewLoadingId] = useState<string | null>(null);
  const [patchActionLoading, setPatchActionLoading] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const projects = await listProjects();
        if (!active) return;
        if (projects.length === 0) {
          setApiOnline(true);
          setMessage("后端在线，暂无项目，当前显示 mock dashboard。");
          return;
        }
        const selectedProject = projects.find((item) => item.id === "demo_project") ?? projects[0];
        const detail = await getProject(selectedProject.id);
        if (!active) return;
        setProject(detail);
        setApiOnline(true);
        setMessage(undefined);
      } catch {
        if (!active) return;
        setProject(mockProject);
        setApiOnline(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  const agentCards = useMemo(() => {
    const currentIndex = workflowOrder.indexOf(project.current_step);
    const completed = project.workflow_status === "completed";
    const status = (step: string) => {
      const index = workflowOrder.indexOf(step);
      if (completed || index < currentIndex) return "已完成" as const;
      if (index === currentIndex && project.workflow_status === "running") return "进行中" as const;
      return "待处理" as const;
    };
    return [
      {
        title: "Literature Agent",
        description: "生成文献综述草稿、metadata 索引和 PDF 质量提示。",
        icon: SearchCheck,
        status: status("literature")
      },
      {
        title: "Analysis Agent",
        description: "读取 CSV，输出基础统计和 analysis provenance。",
        icon: Database,
        status: status("analysis")
      },
      {
        title: "Claim Alignment Agent",
        description: "扫描正文句子并对齐 evidence claim。",
        icon: GitCompareArrows,
        status: status("claim_alignment")
      },
      {
        title: "Reviewer Agent",
        description: "检查证据、图表、引用和句子级风险。",
        icon: AlertTriangle,
        status: status("reviewer")
      }
    ];
  }, [project.current_step, project.workflow_status]);

  async function refreshProject(projectId = project.id) {
    const detail = await getProject(projectId);
    setProject(detail);
  }

  async function handleRunWorkflow() {
    if (!apiOnline) {
      setMessage("后端不可用，无法触发真实 workflow。");
      return;
    }
    setRunning(true);
    setMessage("工作流已提交，正在生成分析、图表、论文草稿、claim alignment 和审稿报告。");
    try {
      const result = await runWorkflow(project.id);
      await refreshProject(result.project_id);
      setMessage("工作流完成，最新输出已刷新。");
    } catch {
      setMessage("工作流运行失败，请检查 FastAPI 服务日志。");
    } finally {
      setRunning(false);
    }
  }

  async function handleUpload(kind: "literature" | "data", file: File) {
    if (!apiOnline) {
      setMessage("后端不可用，当前仅显示 mock 数据。");
      return;
    }
    try {
      await uploadFile(project.id, kind, file);
      await refreshProject();
      setMessage(kind === "literature" ? "文献已上传。" : "数据集已上传。");
    } catch {
      setMessage("上传失败，请确认文件类型和后端状态。");
    }
  }

  async function handleSelectOutput(output: OutputItem) {
    setSelectedOutput(output);
    setOutputContent(undefined);
    setDetailMode("output");
    setDetailLoading(true);
    try {
      const content = apiOnline ? await getOutput(project.id, output.id) : mockOutputContent(output);
      setOutputContent(content);
    } catch {
      setOutputContent(mockOutputContent(output));
      setMessage("输出详情读取失败，已使用 mock 预览。");
    } finally {
      setDetailLoading(false);
    }
  }

  async function openPanel<T>(mode: DetailMode, loader: () => Promise<T>, apply: (value: T) => void) {
    setDetailMode(mode);
    setDetailLoading(true);
    try {
      apply(await loader());
    } catch {
      setMessage("详情读取失败，已使用 mock 数据。");
    } finally {
      setDetailLoading(false);
    }
  }

  function handleOpenEvidence() {
    void openPanel(
      "evidence",
      () => (apiOnline ? getEvidence(project.id) : Promise.resolve(mockEvidence)),
      setEvidence
    );
  }

  function handleOpenEvidenceClaimReview() {
    setDetailMode("evidenceClaimReview");
    setDetailLoading(true);
    const claimsLoader = apiOnline ? getEvidence(project.id) : Promise.resolve(mockEvidence);
    const reviewsLoader = apiOnline
      ? getEvidenceClaimReviews(project.id)
      : Promise.resolve(mockEvidenceClaimReviews);
    void Promise.all([claimsLoader, reviewsLoader])
      .then(([claims, reviews]) => {
        setEvidence(claims);
        setEvidenceClaimReviews(reviews);
      })
      .catch(() => {
        setEvidence(mockEvidence);
        setEvidenceClaimReviews(mockEvidenceClaimReviews);
        setMessage("Evidence claim review 读取失败，已使用 mock 数据。");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleReviewEvidenceClaim(
    claimId: string,
    status: EvidenceClaimReviewStatus,
    reason: string
  ) {
    setPatchActionLoading(true);
    try {
      if (apiOnline) {
        const recorded = await reviewEvidenceClaim(project.id, claimId, status, reason);
        setEvidenceClaimReviews((current) => ({
          reviews: [
            recorded,
            ...current.reviews.filter((review) => review.review_id !== recorded.review_id)
          ],
          summary: recorded.summary
        }));
      } else {
        const recorded = {
          ...mockEvidenceClaimReviews.reviews[0],
          review_id: `mock_evidence_claim_review_${Date.now()}`,
          claim_id: claimId,
          human_status: status,
          reason,
          created_at: new Date().toISOString()
        };
        setEvidenceClaimReviews((current) => ({
          reviews: [recorded, ...current.reviews],
          summary: {
            ...current.summary,
            summary: {
              ...current.summary.summary,
              reviewed: current.summary.summary.reviewed + 1,
              unreviewed: Math.max(current.summary.summary.unreviewed - 1, 0),
              [status]: current.summary.summary[status] + 1
            },
            claims: current.summary.claims.map((claim) =>
              claim.claim_id === claimId
                ? {
                    ...claim,
                    latest_human_status: status,
                    latest_reason: reason,
                    review_count: claim.review_count + 1
                  }
                : claim
            )
          }
        }));
      }
      setMessage("Evidence claim review 已记录，evidence.json 未被自动修改。");
    } catch {
      setMessage("Evidence claim review 记录失败。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenGlobalTrust() {
    void openPanel(
      "globalTrust",
      () => (apiOnline ? getTrustSummary(project.id) : Promise.resolve(mockTrustSummary)),
      setTrustSummary
    );
  }

  function handleOpenFigureProvenance() {
    void openPanel(
      "figures",
      () => (apiOnline ? getFigureProvenance(project.id) : Promise.resolve(mockFigureProvenance)),
      setFigureProvenance
    );
  }

  function handleOpenClaimAlignment() {
    void openPanel(
      "claimAlignment",
      () => (apiOnline ? getClaimAlignment(project.id) : Promise.resolve(mockClaimAlignment)),
      setClaimAlignment
    );
  }

  function handleOpenSentenceIssues() {
    void openPanel(
      "sentenceIssues",
      () => (apiOnline ? getSentenceIssues(project.id) : Promise.resolve(mockSentenceIssues)),
      setSentenceIssues
    );
  }

  function handleOpenLiterature() {
    void openPanel(
      "literature",
      () => (apiOnline ? getLiterature(project.id) : Promise.resolve(mockLiterature)),
      setLiterature
    );
  }

  function handleOpenLLMSettings() {
    setDetailMode("llmSettings");
    setDetailLoading(true);
    const loadStatus = apiOnline ? getLLMStatus() : Promise.resolve(mockLLMStatus);
    const loadPrompts = apiOnline ? getPromptRegistry() : Promise.resolve(mockPromptRegistry);
    void Promise.all([loadStatus, loadPrompts])
      .then(([status, prompts]) => {
        setLLMStatus(status);
        setPromptRegistry(prompts);
      })
      .catch(() => {
        setLLMStatus(mockLLMStatus);
        setPromptRegistry(mockPromptRegistry);
        setMessage("LLM settings read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleRefreshLLMSettings() {
    try {
      if (apiOnline) {
        setLLMStatus(await getLLMStatus());
        setPromptRegistry(await getPromptRegistry());
      } else {
        setLLMStatus(mockLLMStatus);
        setPromptRegistry(mockPromptRegistry);
      }
    } catch {
      setMessage("LLM settings refresh failed.");
    }
  }

  async function handleTestLLM(prompt: string) {
    setPatchActionLoading(true);
    try {
      const result = apiOnline ? await testLLM(prompt) : mockLLMTestResult;
      setLLMTestResult(result);
      setMessage("LLM test completed without exposing API keys.");
    } catch {
      setLLMTestResult(mockLLMTestResult);
      setMessage("LLM test failed; using mock result.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenLLMCallLog() {
    void openPanel(
      "llmCallLog",
      () => (apiOnline ? getLLMCalls(project.id) : Promise.resolve(mockLLMCalls)),
      setLLMCalls
    );
  }

  function handleOpenLiteratureRAG() {
    setDetailMode("literatureRag");
    setDetailLoading(true);
    const loadChunks = apiOnline
      ? getLiteratureRAGChunks(project.id)
      : Promise.resolve(mockLiteratureRAGChunks);
    const loadAnswers = apiOnline
      ? getLiteratureRAGAnswers(project.id)
      : Promise.resolve(mockLiteratureRAGAnswers);
    void Promise.all([loadChunks, loadAnswers])
      .then(([chunks, answers]) => {
        setLiteratureRagChunks(chunks.length ? chunks : mockLiteratureRAGChunks);
        setLiteratureRagAnswers(answers.length ? answers : mockLiteratureRAGAnswers);
      })
      .catch(() => {
        setLiteratureRagChunks(mockLiteratureRAGChunks);
        setLiteratureRagAnswers(mockLiteratureRAGAnswers);
        setMessage("Literature RAG read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleBuildLiteratureRAG() {
    setPatchActionLoading(true);
    try {
      const index = apiOnline ? await buildLiteratureRAG(project.id) : mockLiteratureRAGIndex;
      const chunks = apiOnline ? await getLiteratureRAGChunks(project.id) : mockLiteratureRAGChunks;
      setLiteratureRagIndex(index);
      setLiteratureRagChunks(chunks.length ? chunks : mockLiteratureRAGChunks);
      setMessage("Literature RAG index built from local parsed text.");
    } catch {
      setLiteratureRagIndex(mockLiteratureRAGIndex);
      setLiteratureRagChunks(mockLiteratureRAGChunks);
      setMessage("Literature RAG build failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleAskLiteratureRAG(question: string) {
    setPatchActionLoading(true);
    try {
      const answer = apiOnline
        ? await askLiteratureRAG(project.id, question, 5, "local_hybrid")
        : mockLiteratureRAGAnswers[0];
      setLiteratureRagAnswers((current) => [
        answer,
        ...current.filter((item) => item.answer_id !== answer.answer_id)
      ]);
      setMessage("Literature RAG answer generated with local hybrid retrieval signals.");
    } catch {
      setLiteratureRagAnswers(mockLiteratureRAGAnswers);
      setMessage("Literature RAG ask failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenRAGQuality() {
    setDetailMode("ragQuality");
    setDetailLoading(true);
    const loadQuality = apiOnline
      ? getRAGChunkQuality(project.id)
      : Promise.resolve(mockRAGChunkQuality);
    const loadEvalSet = apiOnline
      ? getRAGRetrievalEvalSet(project.id)
      : Promise.resolve(mockRAGRetrievalEvalSet);
    const loadEvaluation = apiOnline
      ? getRAGRetrievalEvaluation(project.id)
      : Promise.resolve(mockRAGRetrievalEvaluation);
    void Promise.all([loadQuality, loadEvalSet, loadEvaluation])
      .then(([quality, evalSet, evaluation]) => {
        setRAGChunkQuality(quality);
        setRAGRetrievalEvalSet(evalSet);
        setRAGRetrievalEvaluation(evaluation);
      })
      .catch(() => {
        setRAGChunkQuality(mockRAGChunkQuality);
        setRAGRetrievalEvalSet(mockRAGRetrievalEvalSet);
        setRAGRetrievalEvaluation(mockRAGRetrievalEvaluation);
        setMessage("RAG Quality read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleEvaluateRAGRetrieval() {
    setPatchActionLoading(true);
    try {
      const evaluation = apiOnline
        ? await evaluateRAGRetrieval(project.id)
        : mockRAGRetrievalEvaluation;
      setRAGRetrievalEvaluation(evaluation);
      setMessage("RAG retrieval eval completed with local deterministic cases.");
    } catch {
      setRAGRetrievalEvaluation(mockRAGRetrievalEvaluation);
      setMessage("RAG retrieval eval failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenSourcePassageEvidence() {
    void openPanel(
      "sourcePassageEvidence",
      () =>
        apiOnline
          ? getSourcePassageEvidence(project.id)
          : Promise.resolve(mockSourcePassageEvidence),
      setSourcePassageEvidence
    );
  }

  function handleOpenMetadataLookup() {
    void openPanel(
      "literatureMetadataLookup",
      () =>
        apiOnline
          ? getMetadataLookupResults(project.id)
          : Promise.resolve(mockMetadataLookupResults),
      setMetadataLookupResults
    );
  }

  async function handleRunMetadataLookup() {
    setPatchActionLoading(true);
    try {
      const result = apiOnline
        ? await runMetadataLookup(project.id, metadataLookupProvider)
        : mockMetadataLookupResults;
      setMetadataLookupResults(result);
      setMessage("Metadata lookup completed without modifying literature_index.json.");
    } catch {
      setMetadataLookupResults(mockMetadataLookupResults);
      setMessage("Metadata lookup failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenBibTeX() {
    void openPanel(
      "bibtex",
      () => (apiOnline ? getBibTeX(project.id) : Promise.resolve(mockBibTeX)),
      setBibtex
    );
  }

  async function handleGenerateBibTeX() {
    setPatchActionLoading(true);
    try {
      const result = apiOnline ? await generateBibTeX(project.id) : mockBibTeX;
      setBibtex(result);
      setMessage("BibTeX draft generated with verified-only formal entries.");
    } catch {
      setBibtex(mockBibTeX);
      setMessage("BibTeX generation failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenCitationSupport() {
    void openPanel(
      "citationSupport",
      () => (apiOnline ? getCitationSupport(project.id) : Promise.resolve(mockCitationSupport)),
      setCitationSupport
    );
  }

  function handleOpenReferenceVerification() {
    setDetailMode("referenceVerification");
    setDetailLoading(true);
    const loadResults = apiOnline
      ? getReferenceVerificationResults(project.id)
      : Promise.resolve(mockReferenceVerificationResults);
    const loadSummary = apiOnline
      ? getReferenceVerificationSummary(project.id)
      : Promise.resolve(mockReferenceVerificationSummary);
    void Promise.all([loadResults, loadSummary])
      .then(([results, summary]) => {
        setReferenceVerificationResults(results.length ? results : mockReferenceVerificationResults);
        setReferenceVerificationSummary(summary);
      })
      .catch(() => {
        setReferenceVerificationResults(mockReferenceVerificationResults);
        setReferenceVerificationSummary(mockReferenceVerificationSummary);
        setMessage("Reference verification read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleRunReferenceVerification() {
    setPatchActionLoading(true);
    try {
      const result = apiOnline
        ? await runReferenceVerification(project.id, referenceVerificationProvider)
        : {
            results: mockReferenceVerificationResults,
            summary: mockReferenceVerificationSummary,
            literature_index_modified: false
          };
      setReferenceVerificationResults(result.results.length ? result.results : mockReferenceVerificationResults);
      setReferenceVerificationSummary(result.summary);
      setMessage("Reference verification candidates generated without modifying literature_index.json.");
    } catch {
      setReferenceVerificationResults(mockReferenceVerificationResults);
      setReferenceVerificationSummary(mockReferenceVerificationSummary);
      setMessage("Reference verification failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenReferenceApproval() {
    setDetailMode("referenceApproval");
    setDetailLoading(true);
    const loadResults = apiOnline
      ? getReferenceVerificationResults(project.id)
      : Promise.resolve(mockReferenceVerificationResults);
    const loadApprovals = apiOnline
      ? getReferenceApprovals(project.id)
      : Promise.resolve(mockReferenceApprovals);
    const loadSummary = apiOnline
      ? getReferenceApprovalSummary(project.id)
      : Promise.resolve(mockReferenceApprovalSummary);
    void Promise.all([loadResults, loadApprovals, loadSummary])
      .then(([results, approvals, summary]) => {
        setReferenceVerificationResults(results.length ? results : mockReferenceVerificationResults);
        setReferenceApprovals(approvals.length ? approvals : mockReferenceApprovals);
        setReferenceApprovalSummary(summary);
      })
      .catch(() => {
        setReferenceVerificationResults(mockReferenceVerificationResults);
        setReferenceApprovals(mockReferenceApprovals);
        setReferenceApprovalSummary(mockReferenceApprovalSummary);
        setMessage("Reference approval read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleReferenceApprovalDecision(
    verificationId: string,
    decision: ReferenceApprovalDecision,
    applyToLiteratureIndex: boolean
  ) {
    setPatchActionLoading(true);
    try {
      const result = apiOnline
        ? await approveReferenceVerification(
            project.id,
            verificationId,
            decision,
            applyToLiteratureIndex
              ? "Human approved and explicitly applied to literature_index.json."
              : "Human decision recorded without applying to literature_index.json.",
            applyToLiteratureIndex
          )
        : {
            ...mockReferenceApprovals[0],
            approval_id: `ref_approval_${Date.now()}`,
            verification_id: verificationId,
            decision,
            apply_to_literature_index: applyToLiteratureIndex,
            applied_to_literature_index: false,
            literature_index_modified: false,
            summary: mockReferenceApprovalSummary,
            applied_record: null
          };
      setReferenceApprovals((current) => [result, ...current]);
      setReferenceApprovalSummary(result.summary);
      if (apiOnline) {
        const results = await getReferenceVerificationResults(project.id);
        setReferenceVerificationResults(results);
      }
      setMessage(
        applyToLiteratureIndex
          ? "Reference approval applied to literature_index.json with metadata history."
          : "Reference approval recorded without modifying literature_index.json."
      );
    } catch {
      setMessage("Reference approval action failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenCitationGrounding() {
    void openPanel(
      "citationGrounding",
      () => (apiOnline ? getCitationGrounding(project.id) : Promise.resolve(mockCitationGrounding)),
      setCitationGrounding
    );
  }

  function handleOpenVerifiedReferences() {
    setDetailMode("verifiedReferences");
    setDetailLoading(true);
    const loadStatus = apiOnline
      ? getManuscriptReferencesStatus(project.id)
      : Promise.resolve(mockManuscriptReferencesStatus);
    const loadPreview = apiOnline
      ? getManuscriptReferencesPreview(project.id)
      : Promise.resolve(mockManuscriptReferencesPreview);
    void Promise.all([loadStatus, loadPreview])
      .then(([status, preview]) => {
        setManuscriptReferencesStatus(status);
        setManuscriptReferencesPreview(preview);
      })
      .catch(() => {
        setManuscriptReferencesStatus(mockManuscriptReferencesStatus);
        setManuscriptReferencesPreview(mockManuscriptReferencesPreview);
        setMessage("Verified references read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleRefreshVerifiedReferences() {
    setPatchActionLoading(true);
    try {
      const status = apiOnline
        ? await getManuscriptReferencesStatus(project.id)
        : mockManuscriptReferencesStatus;
      const preview = apiOnline
        ? await getManuscriptReferencesPreview(project.id)
        : mockManuscriptReferencesPreview;
      setManuscriptReferencesStatus(status);
      setManuscriptReferencesPreview(preview);
      setMessage("Verified References preview refreshed without overwriting draft.md.");
    } catch {
      setManuscriptReferencesStatus(mockManuscriptReferencesStatus);
      setManuscriptReferencesPreview(mockManuscriptReferencesPreview);
      setMessage("Verified References refresh failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenAnalysisProvenance() {
    void openPanel(
      "analysisProvenance",
      () => (apiOnline ? getAnalysisProvenance(project.id) : Promise.resolve(mockAnalysisProvenance)),
      setAnalysisProvenance
    );
  }

  function handleOpenStatisticalAssistant() {
    void openPanel(
      "statisticalAssistant",
      () =>
        apiOnline
          ? getStatisticalAssistant(project.id)
          : Promise.resolve(mockStatisticalAssistantReport),
      setStatisticalAssistant
    );
  }

  async function handleGenerateStatisticalAssistant() {
    setPatchActionLoading(true);
    try {
      const report = apiOnline
        ? await generateStatisticalAssistant(project.id)
        : mockStatisticalAssistantReport;
      setStatisticalAssistant(report);
      setMessage("Statistical assistant report generated from local descriptive analysis.");
    } catch {
      setStatisticalAssistant(mockStatisticalAssistantReport);
      setMessage("Statistical assistant generation failed; using mock data.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenRevisionDiff() {
    setDetailMode("revisionDiff");
    setDetailLoading(true);
    const loadIssues = apiOnline ? getSentenceIssues(project.id) : Promise.resolve(mockSentenceIssues);
    const loadDecisions = apiOnline
      ? getRevisionDecisions(project.id)
      : Promise.resolve(mockRevisionDecisions);
    void Promise.all([loadIssues, loadDecisions])
      .then(([issues, decisions]) => {
        setSentenceIssues(issues);
        setRevisionDecisions(decisions);
      })
      .catch(() => {
        setSentenceIssues(mockSentenceIssues);
        setRevisionDecisions(mockRevisionDecisions);
        setMessage("修订建议读取失败，已使用 mock 数据。");
      })
      .finally(() => setDetailLoading(false));
  }

  function handleOpenManuscriptPatch() {
    setDetailMode("manuscriptPatch");
    setDetailLoading(true);
    const loadPatches = apiOnline
      ? getManuscriptPatches(project.id)
      : Promise.resolve(mockManuscriptPatches);
    void loadPatches
      .then(async (patches) => {
        setManuscriptPatches(patches);
        const firstPatch = patches[0];
        setSelectedPatch(firstPatch);
        setSelectedPatchItem(firstPatch?.items[0]);
        if (!firstPatch) {
          setPatchPreview(undefined);
          return;
        }
        const preview = apiOnline
          ? await getManuscriptPatchPreview(project.id, firstPatch.patch_id)
          : mockManuscriptPatchPreview;
        setPatchPreview(preview);
      })
      .catch(() => {
        setManuscriptPatches(mockManuscriptPatches);
        setSelectedPatch(mockManuscriptPatches[0]);
        setSelectedPatchItem(mockManuscriptPatches[0]?.items[0]);
        setPatchPreview(mockManuscriptPatchPreview);
        setMessage("Manuscript Patch 璇诲彇澶辫触锛屽凡浣跨敤 mock 鏁版嵁銆?");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleGenerateManuscriptPatch() {
    setPatchActionLoading(true);
    try {
      const patch = apiOnline
        ? await generateManuscriptPatch(project.id)
        : {
            ...mockManuscriptPatches[0],
            patch_id: `patch_mock_${Date.now()}`,
            created_at: new Date().toISOString(),
            status: "proposed"
          };
      const preview = apiOnline
        ? await getManuscriptPatchPreview(project.id, patch.patch_id)
        : { ...mockManuscriptPatchPreview, patch_id: patch.patch_id };
      setManuscriptPatches((current) => [patch, ...current.filter((item) => item.patch_id !== patch.patch_id)]);
      setSelectedPatch(patch);
      setSelectedPatchItem(patch.items[0]);
      setPatchPreview(preview);
      setMessage("Manuscript patch 宸茬敓鎴愶紝draft.md 鏈淇敼銆?");
    } catch {
      setMessage("Manuscript patch 鐢熸垚澶辫触锛岃纭宸叉湁 accepted revision decision銆?");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleSelectPatch(patchId: string) {
    setPatchActionLoading(true);
    try {
      const patch = apiOnline
        ? await getManuscriptPatch(project.id, patchId)
        : manuscriptPatches.find((item) => item.patch_id === patchId) ?? mockManuscriptPatches[0];
      const preview = apiOnline
        ? await getManuscriptPatchPreview(project.id, patchId)
        : { ...mockManuscriptPatchPreview, patch_id: patchId };
      setSelectedPatch(patch);
      setSelectedPatchItem(patch.items[0]);
      setPatchPreview(preview);
    } catch {
      setMessage("Patch preview 璇诲彇澶辫触銆?");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleConfirmPatch(patchId: string, decision: "confirmed" | "rejected") {
    setPatchActionLoading(true);
    try {
      const result = apiOnline
        ? await confirmManuscriptPatch(project.id, patchId, {
            decision,
            reason: "Recorded from ResearchAgent dashboard."
          })
        : {
            patch: {
              ...(manuscriptPatches.find((item) => item.patch_id === patchId) ?? mockManuscriptPatches[0]),
              status: decision
            },
            version: decision === "confirmed" ? mockManuscriptVersionHistory.versions[0] : null
          };
      setManuscriptPatches((current) =>
        current.map((item) => (item.patch_id === patchId ? result.patch : item))
      );
      setSelectedPatch(result.patch);
      setSelectedPatchItem(result.patch.items[0]);
      if (apiOnline) {
        const preview = await getManuscriptPatchPreview(project.id, patchId);
        setPatchPreview(preview);
        const versions = await getManuscriptVersions(project.id);
        setManuscriptVersions(versions);
      } else if (result.version) {
        setManuscriptVersions(mockManuscriptVersionHistory);
        setSelectedVersion(mockManuscriptVersionContent);
      }
      setMessage(
        decision === "confirmed"
          ? "Patch 宸茬‘璁わ紝宸茬敓鎴愭柊 manuscript version锛宒raft.md 鏈瑕嗙洊銆?"
          : "Patch 宸叉嫆缁濓紝涓嶄細鐢熸垚 manuscript version銆?"
      );
    } catch {
      setMessage("Patch 纭鎴栨嫆缁濆け璐ャ€?");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenManuscriptVersions() {
    setDetailMode("manuscriptVersions");
    setDetailLoading(true);
    const loadVersions = apiOnline
      ? getManuscriptVersions(project.id)
      : Promise.resolve(mockManuscriptVersionHistory);
    void loadVersions
      .then(async (history) => {
        setManuscriptVersions(history);
        const firstVersion = history.versions[0];
        if (!firstVersion) {
          setSelectedVersion(undefined);
          return;
        }
        const content = apiOnline
          ? await getManuscriptVersion(project.id, firstVersion.version_id)
          : mockManuscriptVersionContent;
        setSelectedVersion(content);
      })
      .catch(() => {
        setManuscriptVersions(mockManuscriptVersionHistory);
        setSelectedVersion(mockManuscriptVersionContent);
        setMessage("Manuscript version 璇诲彇澶辫触锛屽凡浣跨敤 mock 鏁版嵁銆?");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleSelectVersion(versionId: string) {
    setDetailLoading(true);
    try {
      const content = apiOnline
        ? await getManuscriptVersion(project.id, versionId)
        : mockManuscriptVersionContent;
      setSelectedVersion(content);
    } catch {
      setMessage("Manuscript version content 璇诲彇澶辫触銆?");
    } finally {
      setDetailLoading(false);
    }
  }

  function handleOpenVersionLineage() {
    void openPanel(
      "versionLineage",
      () => (apiOnline ? getVersionLineage(project.id) : Promise.resolve(mockVersionLineage)),
      setVersionLineage
    );
  }

  function handleOpenAuditVerify() {
    void openPanel(
      "auditVerify",
      () => (apiOnline ? verifyAuditLog(project.id) : Promise.resolve(mockAuditVerify)),
      setAuditVerify
    );
  }

  function handleOpenReadinessReport() {
    void openPanel(
      "readinessReport",
      () => (apiOnline ? getReadinessReport(project.id) : Promise.resolve(mockReadinessReport)),
      setReadinessReport
    );
  }

  function handleOpenReleaseReadiness() {
    void openPanel(
      "releaseReadiness",
      () => (apiOnline ? getReadinessReport(project.id) : Promise.resolve(mockReadinessReport)),
      setReadinessReport
    );
  }

  function handleRunLocalValidation() {
    setMessage("本地校验命令：python scripts/validate_v1.py");
  }

  function handleOpenProjectExport() {
    void openPanel(
      "projectExport",
      () => (apiOnline ? getProjectExport(project.id) : Promise.resolve(mockProjectExport)),
      setProjectExport
    );
  }

  async function handleRefreshProjectExport() {
    setDetailLoading(true);
    try {
      const latest = apiOnline ? await getProjectExport(project.id) : mockProjectExport;
      setProjectExport(latest);
    } catch {
      setProjectExport(mockProjectExport);
      setMessage("项目导出信息读取失败，已使用 mock 数据。");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleCreateProjectExport() {
    setPatchActionLoading(true);
    try {
      const created = apiOnline ? await createProjectExport(project.id) : mockProjectExport;
      setProjectExport(created);
      setDetailMode("projectExport");
      setMessage(`Project export created: ${created.relative_path ?? "mock export"}`);
    } catch {
      setMessage("Project export 生成失败，请检查后端服务和 demo_project。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleRefreshAuditVerify() {
    setDetailLoading(true);
    try {
      setAuditVerify(apiOnline ? await verifyAuditLog(project.id) : mockAuditVerify);
    } catch {
      setAuditVerify(mockAuditVerify);
      setMessage("Audit hash chain 鏍￠獙澶辫触锛屽凡浣跨敤 mock 缁撴灉銆?");
    } finally {
      setDetailLoading(false);
    }
  }

  function replacePatch(updatedPatch: ManuscriptPatch) {
    setManuscriptPatches((current) =>
      current.map((item) => (item.patch_id === updatedPatch.patch_id ? updatedPatch : item))
    );
    setSelectedPatch(updatedPatch);
    setSelectedPatchItem(updatedPatch.items[0]);
  }

  function handleOpenPatchItemEditor(patch: ManuscriptPatch, item: ManuscriptPatchItem) {
    setSelectedPatch(patch);
    setSelectedPatchItem(item);
    setDetailMode("patchItemEditor");
  }

  async function handleSavePatchItem(
    patchId: string,
    itemId: string,
    after: string,
    reason: string
  ) {
    setPatchActionLoading(true);
    try {
      const updatedPatch = apiOnline
        ? await editManuscriptPatchItem(project.id, patchId, itemId, { after, reason })
        : {
            ...(selectedPatch ?? mockManuscriptPatches[0]),
            items: (selectedPatch ?? mockManuscriptPatches[0]).items.map((item) =>
              item.patch_item_id === itemId
                ? {
                    ...item,
                    after,
                    item_status: "safe",
                    manual_edits: [
                      ...(item.manual_edits ?? []),
                      {
                        edit_id: `patch_edit_${(item.manual_edits?.length ?? 0) + 1}`,
                        old_after: item.after,
                        new_after: after,
                        reason,
                        created_at: new Date().toISOString(),
                        safety_result: { safe: true, warnings: [], blocked_reasons: [] }
                      }
                    ],
                    latest_safety_result: { safe: true, warnings: [], blocked_reasons: [] }
                  }
                : item
            )
          };
      replacePatch(updatedPatch);
      setSelectedPatchItem(updatedPatch.items.find((item) => item.patch_item_id === itemId));
      if (apiOnline) {
        setPatchPreview(await getManuscriptPatchPreview(project.id, patchId));
      }
      setMessage("Patch item 已保存，并完成 safety check。");
    } catch {
      setMessage("Patch item 保存失败，请检查 patch 状态和 after 文本。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleSafetyCheckPatchItem(patchId: string, itemId: string) {
    setPatchActionLoading(true);
    try {
      const result = apiOnline
        ? await safetyCheckManuscriptPatchItem(project.id, patchId, itemId)
        : {
            patch: selectedPatch ?? mockManuscriptPatches[0],
            patch_item: selectedPatchItem ?? mockManuscriptPatches[0].items[0],
            safety_result: { safe: true, warnings: [], blocked_reasons: [] }
          };
      replacePatch(result.patch);
      setSelectedPatchItem(result.patch.items.find((item) => item.patch_item_id === itemId));
      setMessage(`Safety check: ${String(result.safety_result.safe)}`);
    } catch {
      setMessage("Patch item safety check 失败。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenPatchConflicts() {
    setDetailMode("patchConflicts");
    void openPanel(
      "patchConflicts",
      () => (apiOnline ? getManuscriptPatches(project.id) : Promise.resolve(mockManuscriptPatches)),
      (patches) => {
        setManuscriptPatches(patches);
        setPatchConflictReport(apiOnline ? undefined : mockPatchConflictReport);
      }
    );
  }

  async function handleCheckPatchConflicts(patchIds: string[]) {
    setPatchActionLoading(true);
    try {
      const report = apiOnline
        ? await checkPatchConflicts(project.id, patchIds)
        : { ...mockPatchConflictReport, patch_ids: patchIds };
      setPatchConflictReport(report);
      setMessage("Patch conflict report 已生成。");
    } catch {
      setMessage("Patch conflict check 失败。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenPatchMerge() {
    setDetailMode("patchMerge");
    void openPanel(
      "patchMerge",
      () => (apiOnline ? getManuscriptPatches(project.id) : Promise.resolve(mockManuscriptPatches)),
      (patches) => {
        setManuscriptPatches(patches);
        setPatchMergePreview(apiOnline ? undefined : mockPatchMergePreview);
      }
    );
  }

  async function handleGeneratePatchMerge(patchIds: string[]) {
    setPatchActionLoading(true);
    try {
      const merge = apiOnline
        ? await generatePatchMergePreview(project.id, patchIds)
        : { ...mockPatchMergePreview, patch_ids: patchIds };
      setPatchMergePreview(merge);
      setMessage("Patch merge preview 已生成，draft.md 未被修改。");
    } catch {
      setMessage("Patch merge preview 生成失败。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleConfirmPatchMerge(mergeId: string, decision: "confirmed" | "rejected") {
    setPatchActionLoading(true);
    try {
      const result = apiOnline
        ? await confirmPatchMerge(project.id, mergeId, {
            decision,
            reason: "Recorded from ResearchAgent dashboard."
          })
        : {
            merge: {
              ...mockPatchMergePreview,
              merge_id: mergeId,
              status: decision,
              generated_version_id:
                decision === "confirmed" ? mockManuscriptVersionHistory.versions[0].version_id : null,
              generated_diff_id: decision === "confirmed" ? mockManuscriptDiffs[0].diff_id : null
            },
            version: decision === "confirmed" ? mockManuscriptVersionHistory.versions[0] : null,
            diff: decision === "confirmed" ? mockManuscriptDiffs[0] : null
          };
      setPatchMergePreview(result.merge);
      if (result.version) {
        const versions = apiOnline ? await getManuscriptVersions(project.id) : mockManuscriptVersionHistory;
        setManuscriptVersions(versions);
      }
      if (result.diff) {
        const diffs = apiOnline ? await getManuscriptDiffs(project.id) : mockManuscriptDiffs;
        setManuscriptDiffs(diffs);
      }
      const lineage = apiOnline ? await getVersionLineage(project.id) : mockVersionLineage;
      setVersionLineage(lineage);
      setMessage(decision === "confirmed" ? "Patch merge confirmed; version created." : "Patch merge rejected.");
    } catch {
      setMessage("Patch merge confirmation failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenManuscriptDiff() {
    setDetailMode("manuscriptDiff");
    setDetailLoading(true);
    const loadVersions = apiOnline
      ? getManuscriptVersions(project.id)
      : Promise.resolve(mockManuscriptVersionHistory);
    const loadDiffs = apiOnline ? getManuscriptDiffs(project.id) : Promise.resolve(mockManuscriptDiffs);
    void Promise.all([loadVersions, loadDiffs])
      .then(async ([history, diffs]) => {
        setManuscriptVersions(history);
        setManuscriptDiffs(diffs);
        const firstDiff = diffs[0];
        setSelectedManuscriptDiff(firstDiff);
        if (firstDiff) {
          setManuscriptDiffPreview(
            apiOnline ? await getManuscriptDiffPreview(project.id, firstDiff.diff_id) : mockManuscriptDiffPreview
          );
        }
      })
      .catch(() => {
        setManuscriptVersions(mockManuscriptVersionHistory);
        setManuscriptDiffs(mockManuscriptDiffs);
        setSelectedManuscriptDiff(mockManuscriptDiffs[0]);
        setManuscriptDiffPreview(mockManuscriptDiffPreview);
        setMessage("Manuscript diff 读取失败，已使用 mock 数据。");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleGenerateManuscriptDiff(versionId: string) {
    setPatchActionLoading(true);
    try {
      const diff = apiOnline
        ? await generateManuscriptDiff(project.id, versionId)
        : { ...mockManuscriptDiffs[0], diff_id: `diff_mock_${Date.now()}`, version_id: versionId };
      const preview = apiOnline
        ? await getManuscriptDiffPreview(project.id, diff.diff_id)
        : { ...mockManuscriptDiffPreview, diff_id: diff.diff_id };
      setManuscriptDiffs((current) => [diff, ...current.filter((item) => item.diff_id !== diff.diff_id)]);
      setSelectedManuscriptDiff(diff);
      setManuscriptDiffPreview(preview);
      setDetailMode("manuscriptDiff");
      setMessage("Manuscript diff 已生成。");
    } catch {
      setMessage("Manuscript diff 生成失败。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleSelectManuscriptDiff(diffId: string) {
    setDetailLoading(true);
    try {
      const diff = apiOnline
        ? await getManuscriptDiff(project.id, diffId)
        : manuscriptDiffs.find((item) => item.diff_id === diffId) ?? mockManuscriptDiffs[0];
      const preview = apiOnline
        ? await getManuscriptDiffPreview(project.id, diffId)
        : { ...mockManuscriptDiffPreview, diff_id: diffId };
      setSelectedManuscriptDiff(diff);
      setManuscriptDiffPreview(preview);
    } catch {
      setMessage("Manuscript diff 读取失败。");
    } finally {
      setDetailLoading(false);
    }
  }

  function handleOpenRevisionLineDiff() {
    setDetailMode("revisionLineDiff");
    setDetailLoading(true);
    const loadVersions = apiOnline
      ? getManuscriptVersions(project.id)
      : Promise.resolve(mockManuscriptVersionHistory);
    const loadDiffs = apiOnline
      ? getRevisionLineDiffs(project.id)
      : Promise.resolve(mockRevisionLineDiffs);
    void Promise.all([loadVersions, loadDiffs])
      .then(([history, diffs]) => {
        setManuscriptVersions(history);
        setRevisionLineDiffs(diffs);
        setSelectedRevisionLineDiff(diffs[0]);
      })
      .catch(() => {
        setManuscriptVersions(mockManuscriptVersionHistory);
        setRevisionLineDiffs(mockRevisionLineDiffs);
        setSelectedRevisionLineDiff(mockRevisionLineDiffs[0]);
        setMessage("Revision line diff read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleGenerateRevisionLineDiff(targetFile: string) {
    setPatchActionLoading(true);
    try {
      const diff = apiOnline
        ? await generateRevisionLineDiff(project.id, targetFile)
        : {
            ...mockRevisionLineDiffs[0],
            revision_diff_id: `revision_diff_mock_${Date.now()}`,
            target_file: targetFile
          };
      setRevisionLineDiffs((current) => [
        diff,
        ...current.filter((item) => item.revision_diff_id !== diff.revision_diff_id)
      ]);
      setSelectedRevisionLineDiff(diff);
      setDetailMode("revisionLineDiff");
      setMessage("Revision line diff generated without modifying manuscript files.");
    } catch {
      setMessage("Revision line diff generation failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleSelectRevisionLineDiff(revisionDiffId: string) {
    setDetailLoading(true);
    try {
      const diff = apiOnline
        ? await getRevisionLineDiff(project.id, revisionDiffId)
        : revisionLineDiffs.find((item) => item.revision_diff_id === revisionDiffId) ??
          mockRevisionLineDiffs[0];
      setSelectedRevisionLineDiff(diff);
    } catch {
      setMessage("Revision line diff read failed.");
    } finally {
      setDetailLoading(false);
    }
  }

  function handleOpenRevisionDiffReview() {
    setDetailMode("revisionDiffReview");
    setDetailLoading(true);
    const loadDiffs = apiOnline
      ? getRevisionLineDiffs(project.id)
      : Promise.resolve(mockRevisionLineDiffs);
    const loadReviews = apiOnline
      ? getRevisionDiffReviews(project.id)
      : Promise.resolve(mockRevisionDiffReviews);
    void Promise.all([loadDiffs, loadReviews])
      .then(([diffs, reviews]) => {
        setRevisionLineDiffs(diffs);
        setRevisionDiffReviews(reviews);
      })
      .catch(() => {
        setRevisionLineDiffs(mockRevisionLineDiffs);
        setRevisionDiffReviews(mockRevisionDiffReviews);
        setMessage("Revision diff review read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  function handleOpenReviewerClosure() {
    void openPanel(
      "reviewerClosure",
      () =>
        apiOnline
          ? getReviewerClosureSummary(project.id)
          : Promise.resolve(mockReviewerClosureSummary),
      setReviewerClosure
    );
  }

  async function handleReviewRevisionDiffChange(
    revisionDiffId: string,
    changeId: string,
    status: RevisionDiffHumanStatus
  ) {
    setPatchActionLoading(true);
    try {
      if (apiOnline) {
        const result = await reviewRevisionDiffChange(
          project.id,
          revisionDiffId,
          changeId,
          status,
          "Recorded from ResearchAgent dashboard."
        );
        setRevisionDiffReviews((current) => ({
          reviews: [result, ...current.reviews],
          summary: result.summary
        }));
      } else {
        setRevisionDiffReviews(mockRevisionDiffReviews);
      }
      setMessage("Revision diff review recorded without modifying manuscript files.");
    } catch {
      setMessage("Revision diff review failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenIssueResolution() {
    void openPanel(
      "issueResolution",
      () => (apiOnline ? getIssueResolution(project.id) : Promise.resolve(mockIssueResolution)),
      setIssueResolution
    );
  }

  async function handleIssueResolutionReview(
    issueId: string,
    versionId: string,
    status: "resolved" | "unresolved" | "needs_review"
  ) {
    setIssueReviewLoadingId(`${versionId}:${issueId}`);
    try {
      const result = apiOnline
        ? await recordIssueResolutionReview(project.id, issueId, {
            version_id: versionId,
            human_status: status,
            reason: "Recorded from ResearchAgent dashboard."
          })
        : {
            review: {
              review_id: `issue_review_mock_${Date.now()}`,
              issue_id: issueId,
              version_id: versionId,
              auto_status: "mock",
              human_status: status,
              reason: "Mock dashboard review.",
              created_at: new Date().toISOString(),
              source: "frontend"
            },
            issue_resolution: mockIssueResolution
          };
      setIssueResolution(result.issue_resolution);
      setMessage("Issue resolution human review recorded.");
    } catch {
      setMessage("Issue resolution human review failed.");
    } finally {
      setIssueReviewLoadingId(null);
    }
  }

  function handleOpenAuditExport() {
    setDetailMode("auditExport");
    setDetailLoading(true);
    const loadExports = apiOnline ? getAuditExports(project.id) : Promise.resolve(mockAuditExports);
    void loadExports
      .then(async (exports) => {
        setAuditExports(exports);
        const firstExport = exports[0];
        if (!firstExport) {
          setSelectedAuditExport(undefined);
          setAuditExportReport(undefined);
          setAuditFileManifest(undefined);
          return;
        }
        const selected = apiOnline ? await getAuditExport(project.id, firstExport.export_id) : mockAuditExport;
        const report = apiOnline
          ? await getAuditExportReport(project.id, firstExport.export_id)
          : mockAuditExportReport;
        const manifest = apiOnline
          ? await getAuditFileManifest(project.id, firstExport.export_id)
          : mockAuditFileManifest;
        setSelectedAuditExport(selected);
        setAuditExportReport(report);
        setAuditFileManifest(manifest);
      })
      .catch(() => {
        setAuditExports(mockAuditExports);
        setSelectedAuditExport(mockAuditExport);
        setAuditExportReport(mockAuditExportReport);
        setAuditFileManifest(mockAuditFileManifest);
        setMessage("Audit export 读取失败，已使用 mock 数据。");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleCreateAuditExport() {
    setPatchActionLoading(true);
    try {
      const created = apiOnline ? await createAuditExport(project.id) : mockAuditExport;
      const report = apiOnline
        ? await getAuditExportReport(project.id, created.export_id)
        : mockAuditExportReport;
      const manifest = apiOnline
        ? await getAuditFileManifest(project.id, created.export_id)
        : mockAuditFileManifest;
      const exports = apiOnline ? await getAuditExports(project.id) : mockAuditExports;
      setAuditExports(exports);
      setSelectedAuditExport(created);
      setAuditExportReport(report);
      setAuditFileManifest(manifest);
      setMessage("Audit export 已生成。");
    } catch {
      setMessage("Audit export 生成失败。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleSelectAuditExport(exportId: string) {
    setDetailLoading(true);
    try {
      const selected = apiOnline ? await getAuditExport(project.id, exportId) : mockAuditExport;
      const report = apiOnline
        ? await getAuditExportReport(project.id, exportId)
        : mockAuditExportReport;
      const manifest = apiOnline
        ? await getAuditFileManifest(project.id, exportId)
        : mockAuditFileManifest;
      setSelectedAuditExport(selected);
      setAuditExportReport(report);
      setAuditFileManifest(manifest);
    } catch {
      setMessage("Audit export 读取失败。");
    } finally {
      setDetailLoading(false);
    }
  }

  function handleOpenAuditFilterExport() {
    setDetailMode("auditFilterExport");
    setDetailLoading(true);
    const loadExports = apiOnline
      ? getAuditFilteredExports(project.id)
      : Promise.resolve(mockAuditFilteredExports);
    void loadExports
      .then(async (exports) => {
        setAuditFilteredExports(exports);
        const firstExport = exports[0];
        if (!firstExport) {
          setSelectedAuditFilteredExport(undefined);
          setAuditFilteredExportReport(undefined);
          return;
        }
        const selected = apiOnline
          ? await getAuditFilteredExport(project.id, firstExport.export_id)
          : mockAuditFilteredExport;
        const report = apiOnline
          ? await getAuditFilteredExportReport(project.id, firstExport.export_id)
          : mockAuditFilteredExportReport;
        setSelectedAuditFilteredExport(selected);
        setAuditFilteredExportReport(report);
      })
      .catch(() => {
        setAuditFilteredExports(mockAuditFilteredExports);
        setSelectedAuditFilteredExport(mockAuditFilteredExport);
        setAuditFilteredExportReport(mockAuditFilteredExportReport);
        setMessage("Filtered audit export read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleCreateAuditFilterExport() {
    setPatchActionLoading(true);
    try {
      const created = apiOnline
        ? await createAuditFilteredExport(project.id, { risk_level: auditFilterRiskLevel })
        : mockAuditFilteredExport;
      const report = apiOnline
        ? await getAuditFilteredExportReport(project.id, created.export_id)
        : mockAuditFilteredExportReport;
      const exports = apiOnline ? await getAuditFilteredExports(project.id) : mockAuditFilteredExports;
      setAuditFilteredExports(exports);
      setSelectedAuditFilteredExport(created);
      setAuditFilteredExportReport(report);
      setMessage("Filtered audit export generated.");
    } catch {
      setMessage("Filtered audit export generation failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleSelectAuditFilterExport(exportId: string) {
    setDetailLoading(true);
    try {
      const selected = apiOnline
        ? await getAuditFilteredExport(project.id, exportId)
        : mockAuditFilteredExport;
      const report = apiOnline
        ? await getAuditFilteredExportReport(project.id, exportId)
        : mockAuditFilteredExportReport;
      setSelectedAuditFilteredExport(selected);
      setAuditFilteredExportReport(report);
    } catch {
      setMessage("Filtered audit export read failed.");
    } finally {
      setDetailLoading(false);
    }
  }

  function handleOpenLiteratureHistory() {
    void openPanel(
      "literatureHistory",
      () => (apiOnline ? getLiteratureHistory(project.id) : Promise.resolve(mockLiteratureHistory)),
      setLiteratureHistory
    );
  }

  function handleOpenLiteratureMetadataDiff() {
    setDetailMode("literatureMetadataDiff");
    setLiteratureMetadataRevertSuggestion(undefined);
    setDetailLoading(true);
    const loader = apiOnline
      ? getLiteratureMetadataDiff(project.id)
      : Promise.resolve(mockLiteratureMetadataDiff);
    void loader
      .then(setLiteratureMetadataDiff)
      .catch(() => {
        setLiteratureMetadataDiff(mockLiteratureMetadataDiff);
        setMessage("Metadata field diff read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleSuggestMetadataRevert(
    literatureId: string,
    field: string,
    sourceHistoryId: string
  ) {
    setPatchActionLoading(true);
    try {
      const suggestion = apiOnline
        ? await suggestLiteratureMetadataRevert(project.id, literatureId, field, sourceHistoryId)
        : {
            literature_id: literatureId,
            field,
            old_value: null,
            new_value: "mock value",
            change_type: "modified",
            source_history_id: sourceHistoryId,
            revert_suggestion: {
              can_revert: true,
              revert_to: null,
              warning: "Mock revert suggestion only; literature_index.json is unchanged."
            },
            applied: false,
            literature_index_modified: false
          };
      setLiteratureMetadataRevertSuggestion(suggestion);
      setMessage("Metadata revert suggestion generated without applying changes.");
    } catch {
      setMessage("Metadata revert suggestion failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenLiteratureMetadataBatch() {
    setDetailMode("literatureMetadataBatch");
    setDetailLoading(true);
    const loader = apiOnline
      ? generateLiteratureMetadataBatchReview(project.id)
      : Promise.resolve(mockLiteratureMetadataBatch);
    void loader
      .then(setLiteratureMetadataBatch)
      .catch(() => {
        setLiteratureMetadataBatch(mockLiteratureMetadataBatch);
        setMessage("Metadata batch review failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  function handleOpenMetadataReviewWorkflow() {
    setDetailMode("metadataReviewWorkflow");
    setDetailLoading(true);
    const loadDiff = apiOnline
      ? getLiteratureMetadataDiff(project.id)
      : Promise.resolve(mockLiteratureMetadataDiff);
    const loadActions = apiOnline
      ? getMetadataReviewActions(project.id)
      : Promise.resolve(mockMetadataReviewActions);
    void Promise.all([loadDiff, loadActions])
      .then(([diff, actions]) => {
        setLiteratureMetadataDiff(diff);
        setMetadataReviewActions(actions);
      })
      .catch(() => {
        setLiteratureMetadataDiff(mockLiteratureMetadataDiff);
        setMetadataReviewActions(mockMetadataReviewActions);
        setMessage("Metadata review workflow read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  function handleOpenMetadataRevertPreview() {
    setDetailMode("metadataRevertPreview");
    setDetailLoading(true);
    const loadDiff = apiOnline
      ? getLiteratureMetadataDiff(project.id)
      : Promise.resolve(mockLiteratureMetadataDiff);
    void loadDiff
      .then((diff) => {
        setLiteratureMetadataDiff(diff);
        setMetadataRevertPreview(mockMetadataRevertPreview);
      })
      .catch(() => {
        setLiteratureMetadataDiff(mockLiteratureMetadataDiff);
        setMetadataRevertPreview(mockMetadataRevertPreview);
        setMessage("Metadata revert preview 读取失败，已使用 mock 数据。");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleMetadataRevertPreview(
    literatureId: string,
    field: string,
    sourceHistoryId: string
  ) {
    setPatchActionLoading(true);
    try {
      const preview = apiOnline
        ? await previewMetadataRevert(project.id, literatureId, field, sourceHistoryId)
        : {
            ...mockMetadataRevertPreview,
            literature_id: literatureId,
            field,
            source_history_id: sourceHistoryId,
            preview_id: `mock_metadata_revert_preview_${Date.now()}`
          };
      setMetadataRevertPreview(preview);
      setMessage("Metadata revert preview 已生成，literature_index.json 未被修改。");
    } catch {
      setMessage("Metadata revert preview 生成失败。");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleMetadataReviewAction(
    literatureId: string,
    field: string,
    action: MetadataReviewActionValue,
    sourceHistoryId: string
  ) {
    setPatchActionLoading(true);
    try {
      if (apiOnline) {
        const result = await reviewMetadataChange(
          project.id,
          literatureId,
          field,
          action,
          sourceHistoryId,
          "Recorded from ResearchAgent dashboard."
        );
        setMetadataReviewActions((current) => ({
          actions: [result, ...current.actions],
          summary: result.summary
        }));
      } else {
        setMetadataReviewActions(mockMetadataReviewActions);
      }
      setMessage("Metadata review action recorded without modifying literature_index.json.");
    } catch {
      setMessage("Metadata review action failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenPDFQuality() {
    void openPanel(
      "pdfQuality",
      () => (apiOnline ? getLiterature(project.id) : Promise.resolve(mockLiterature)),
      setLiterature
    );
  }

  function handleOpenPDFQualityReport() {
    void openPanel(
      "pdfQualityReport",
      () => (apiOnline ? getPDFQualityReport(project.id) : Promise.resolve(mockPDFQualityReport)),
      setPDFQualityReport
    );
  }

  function handleOpenPDFPageReview() {
    setDetailMode("pdfPageReview");
    setDetailLoading(true);
    const loadReport = apiOnline
      ? getPDFQualityReport(project.id)
      : Promise.resolve(mockPDFQualityReport);
    const loadReviews = apiOnline
      ? getPDFPageReviews(project.id)
      : Promise.resolve(mockPDFPageReviews);
    void Promise.all([loadReport, loadReviews])
      .then(([report, reviews]) => {
        setPDFQualityReport(report);
        setPDFPageReviews(reviews);
      })
      .catch(() => {
        setPDFQualityReport(mockPDFQualityReport);
        setPDFPageReviews(mockPDFPageReviews);
        setMessage("PDF page review read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  function handleOpenPDFPageTextPreview() {
    void openPanel(
      "pdfPageTextPreview",
      () =>
        apiOnline
          ? getPDFPageTextPreview(project.id)
          : Promise.resolve(mockPDFPageTextPreview),
      setPDFPageTextPreview
    );
  }

  async function handlePDFPageReview(
    sourceFile: string,
    pageNumber: number,
    status: PDFPageReviewsResponse["reviews"][number]["human_status"]
  ) {
    setPatchActionLoading(true);
    try {
      if (apiOnline) {
        const result = await reviewPDFPage(
          project.id,
          sourceFile,
          pageNumber,
          status,
          "Recorded from ResearchAgent dashboard."
        );
        setPDFPageReviews((current) => ({
          reviews: [result, ...current.reviews],
          summary: result.summary
        }));
      } else {
        setPDFPageReviews(mockPDFPageReviews);
      }
      setMessage("PDF page review recorded; OCR was not executed.");
    } catch {
      setMessage("PDF page review failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  function handleOpenAnalysisCompare() {
    setDetailMode("analysisCompare");
    setDetailLoading(true);
    const loader = apiOnline
      ? getAnalysisComparisons(project.id)
      : Promise.resolve(mockAnalysisComparisons);
    void loader
      .then((comparisons) => {
        setAnalysisComparisons(comparisons);
        setSelectedAnalysisComparison(comparisons[0]);
      })
      .catch(() => {
        setAnalysisComparisons(mockAnalysisComparisons);
        setSelectedAnalysisComparison(mockAnalysisComparisons[0]);
        setMessage("Analysis comparison read failed; using mock data.");
      })
      .finally(() => setDetailLoading(false));
  }

  async function handleGenerateAnalysisCompare() {
    setPatchActionLoading(true);
    try {
      const comparison = apiOnline
        ? await generateAnalysisComparison(project.id)
        : {
            ...mockAnalysisComparisons[0],
            comparison_id: `analysis_compare_mock_${Date.now()}`
          };
      setAnalysisComparisons((current) => [
        comparison,
        ...current.filter((item) => item.comparison_id !== comparison.comparison_id)
      ]);
      setSelectedAnalysisComparison(comparison);
      setDetailMode("analysisCompare");
      setMessage("Analysis comparison generated from existing provenance files.");
    } catch {
      setMessage("Analysis comparison generation failed.");
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleSelectAnalysisComparison(comparisonId: string) {
    setDetailLoading(true);
    try {
      const comparison = apiOnline
        ? await getAnalysisComparison(project.id, comparisonId)
        : analysisComparisons.find((item) => item.comparison_id === comparisonId) ??
          mockAnalysisComparisons[0];
      setSelectedAnalysisComparison(comparison);
    } catch {
      setMessage("Analysis comparison read failed.");
    } finally {
      setDetailLoading(false);
    }
  }

  function handleOpenAnalysisTimeline() {
    void openPanel(
      "analysisTimeline",
      () => (apiOnline ? getEnhancedAnalysisTimeline(project.id) : Promise.resolve(mockAnalysisTimeline)),
      setAnalysisTimeline
    );
  }

  function handleOpenAuditLog() {
    void openPanel(
      "auditLog",
      () => (apiOnline ? getAuditLog(project.id) : Promise.resolve(mockAuditLog)),
      setAuditLog
    );
  }

  function handleOpenRunHistory() {
    void openPanel(
      "runHistory",
      () => (apiOnline ? getRunHistory(project.id) : Promise.resolve(mockRunHistory)),
      setRunHistory
    );
  }

  async function handleRevisionDecision(issueId: string, decision: "accepted" | "rejected") {
    setDecisionLoadingId(issueId);
    try {
      const requestDecision = () =>
        createRevisionDecision(project.id, issueId, {
            decision,
            reason: "Recorded from ResearchAgent dashboard."
          });
      let recorded: RevisionDecision;
      if (apiOnline) {
        recorded = await requestDecision();
      } else {
        try {
          recorded = await requestDecision();
        } catch {
          recorded = {
            decision_id: `mock_decision_${Date.now()}`,
            issue_id: issueId,
            decision,
            before: sentenceIssues.find((issue) => issue.issue_id === issueId)?.revision_diff?.before ?? "",
            after: sentenceIssues.find((issue) => issue.issue_id === issueId)?.revision_diff?.after ?? "",
            reason: "Mock dashboard decision.",
            created_at: new Date().toISOString(),
            source: "frontend",
            applied_to_manuscript: false
          };
        }
      }
      setRevisionDecisions((current) => [...current, recorded]);
      setMessage("修订决策已记录，draft.md 未被自动修改。");
    } catch {
      setMessage("修订决策记录失败，请确认 review_report.json 和 issue_id 存在。");
    } finally {
      setDecisionLoadingId(null);
    }
  }

  async function handleSaveLiterature(literatureId: string, patch: LiteraturePatch) {
    if (!apiOnline) {
      setLiterature((records) =>
        records.map((record) =>
          record.literature_id === literatureId ? { ...record, ...patch } : record
        )
      );
      setMessage("后端不可用，metadata 修改仅保存在 mock 视图。");
      return;
    }
    try {
      const updated = await patchLiterature(project.id, literatureId, patch);
      setLiterature((records) =>
        records.map((record) => (record.literature_id === literatureId ? updated : record))
      );
      setMessage("文献 metadata 已保存。");
    } catch {
      setMessage("文献 metadata 保存失败，请检查 DOI、year 和必填字段。");
    }
  }

  function closeDetails() {
    setDetailMode("none");
  }

  const latestManuscriptVersion =
    manuscriptVersions.versions[manuscriptVersions.versions.length - 1]?.version_id ??
    project.latest_outputs.find((output) => output.relative_path.startsWith("manuscript/"))?.relative_path ??
    "manuscript/draft.md";

  return (
    <div className="app-shell">
      <Sidebar projectName={project.name} createdAt={project.created_at} />
      <div className="min-w-0">
        <Topbar projectName={project.name} apiOnline={apiOnline} />
        <main className="px-4 py-5 sm:px-6 xl:px-8">
          <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
            <div className="min-w-0 space-y-5">
              <section className="panel overflow-hidden p-5">
                <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="text-2xl font-black tracking-normal text-slate-950">
                      ResearchAgent v0.3
                    </div>
                    <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-slate-500">
                      当前工作台聚焦 manuscript、evidence claim 和 reviewer issue 的可信对齐。
                    </p>
                  </div>
                  <div className="grid min-w-[260px] grid-cols-2 gap-3">
                    {quickActions.map(({ label, icon: Icon }) => (
                      <button
                        key={label}
                        className="flex items-center gap-2 rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:border-[#5b6ee1] hover:text-[#4052c6]"
                      >
                        <Icon size={16} />
                        <span className="truncate">{label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </section>

              <LocalMVPOverviewPanel
                project={project}
                trustSummary={trustSummary}
                readinessReport={readinessReport}
                projectExport={projectExport}
                apiOnline={apiOnline}
                latestManuscriptVersion={latestManuscriptVersion}
                onOpenTrust={handleOpenGlobalTrust}
                onOpenReadiness={handleOpenReleaseReadiness}
                onOpenExport={handleOpenProjectExport}
                onRunValidation={handleRunLocalValidation}
              />

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <StatCard label="文献资料" value={String(project.resources.literature_count)} tone="cyan" icon={SearchCheck} />
                <StatCard label="数据集" value={String(project.resources.dataset_count)} tone="green" icon={Database} />
                <StatCard label="图表文件" value={String(project.resources.figure_count)} tone="indigo" icon={LineChart} />
                <StatCard label="审稿报告" value={String(project.resources.review_count)} tone="amber" icon={ShieldCheck} />
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {agentCards.map((agent) => (
                  <AgentCard key={agent.title} {...agent} />
                ))}
              </div>

              <UploadPanel running={running} onRunWorkflow={handleRunWorkflow} onUpload={handleUpload} />
              <WorkflowTimeline />
              <ResourcePanel resources={project.resources} />
              <TaskCenter />
            </div>

            <aside className="min-w-0 space-y-5">
              <ProgressPanel />
              <RecentOutputs outputs={project.latest_outputs} onSelect={handleSelectOutput} />
              <section className="panel p-5">
                <div className="mb-4 flex items-center gap-2">
                  <ShieldCheck size={19} className="text-[#5b6ee1]" />
                  <h2 className="text-lg font-black">可信链路</h2>
                </div>
                <div className="grid gap-2">
                  <div className="mt-1 text-xs font-black uppercase text-slate-400">Evidence</div>
                  <button className="secondary-button justify-start" onClick={handleOpenEvidence}>
                    <ShieldCheck size={16} />
                    <span>查看证据链</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenEvidenceClaimReview}
                    aria-label="Evidence Claim Review"
                  >
                    <ShieldCheck size={16} />
                    <span>Evidence Claim Review</span>
                  </button>
                  <div className="mt-3 text-xs font-black uppercase text-slate-400">Overview</div>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenGlobalTrust}
                    aria-label="Global Trust Dashboard"
                  >
                    <ShieldCheck size={16} />
                    <span>Global Trust Dashboard</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenReleaseReadiness}
                    aria-label="Release Readiness"
                  >
                    <FileCheck2 size={16} />
                    <span>Release Readiness</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenProjectExport}
                    aria-label="Project Export"
                  >
                    <FileArchive size={16} />
                    <span>Project Export</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleRunLocalValidation}
                    aria-label="Validate Local MVP"
                  >
                    <TerminalSquare size={16} />
                    <span>Validate Local MVP</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenFigureProvenance}>
                    <LineChart size={16} />
                    <span>查看图表来源</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenClaimAlignment}>
                    <GitCompareArrows size={16} />
                    <span>查看 Claim 对齐</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenSentenceIssues}>
                    <AlertTriangle size={16} />
                    <span>查看句子级审稿问题</span>
                  </button>
                  <div className="mt-3 text-xs font-black uppercase text-slate-400">Literature</div>
                  <button className="secondary-button justify-start" onClick={handleOpenLiterature}>
                    <BookOpenCheck size={16} />
                    <span>文献元数据核验</span>
                  </button>
                  <div className="mt-3 text-xs font-black uppercase text-slate-400">
                    Literature Intelligence
                  </div>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenLLMSettings}
                    aria-label="LLM Settings"
                  >
                    <Bot size={16} />
                    <span>LLM Settings</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenLLMSettings}
                    aria-label="Prompt Registry"
                  >
                    <BrainCircuit size={16} />
                    <span>Prompt Registry</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenLiteratureRAG}
                    aria-label="Literature RAG"
                  >
                    <SearchCheck size={16} />
                    <span>Literature RAG</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenRAGQuality}
                    aria-label="RAG Quality"
                  >
                    <BarChart3 size={16} />
                    <span>RAG Quality</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenSourcePassageEvidence}
                    aria-label="Source Passage Evidence"
                  >
                    <FileText size={16} />
                    <span>Source Passage Evidence</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenMetadataLookup}
                    aria-label="Metadata Lookup"
                  >
                    <Database size={16} />
                    <span>Metadata Lookup</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={() => {
                      setDetailMode("referenceVerification");
                      void handleRunReferenceVerification();
                    }}
                    aria-label="Run Reference Verification"
                  >
                    <SearchCheck size={16} />
                    <span>Run Reference Verification</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenReferenceVerification}
                    aria-label="Verification Results"
                  >
                    <SearchCheck size={16} />
                    <span>Verification Results</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenReferenceApproval}
                    aria-label="Approval Workflow"
                  >
                    <ClipboardCheck size={16} />
                    <span>Approval Workflow</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenVerifiedReferences}
                    aria-label="Verified References"
                  >
                    <BookOpenCheck size={16} />
                    <span>Verified References</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenCitationGrounding}
                    aria-label="Citation Grounding"
                  >
                    <Link2 size={16} />
                    <span>Citation Grounding</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenBibTeX}
                    aria-label="BibTeX Status"
                  >
                    <BookOpenCheck size={16} />
                    <span>BibTeX Status</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenBibTeX}
                    aria-label="BibTeX"
                  >
                    <BookOpenCheck size={16} />
                    <span>BibTeX</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenCitationSupport}
                    aria-label="Citation Support"
                  >
                    <ShieldCheck size={16} />
                    <span>Citation Support</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenLLMCallLog}
                    aria-label="LLM Call Log"
                  >
                    <ScrollText size={16} />
                    <span>LLM Call Log</span>
                  </button>
                  <div className="mt-3 text-xs font-black uppercase text-slate-400">Analysis</div>
                  <button className="secondary-button justify-start" onClick={handleOpenAnalysisProvenance}>
                    <Activity size={16} />
                    <span>查看分析来源</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenStatisticalAssistant}
                    aria-label="Statistical Assistant"
                  >
                    <BarChart3 size={16} />
                    <span>Statistical Assistant</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenAnalysisCompare}>
                    <Activity size={16} />
                    <span>Analysis 运行对比</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenAnalysisTimeline}
                    aria-label="Analysis Timeline"
                  >
                    <History size={16} />
                    <span>Analysis Timeline</span>
                  </button>
                  <div className="mt-3 text-xs font-black uppercase text-slate-400">Manuscript</div>
                  <button className="secondary-button justify-start" onClick={handleOpenRevisionDiff}>
                    <GitCompareArrows size={16} />
                    <span>查看修订建议</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenManuscriptPatch}>
                    <PenLine size={16} />
                    <span>查看 Manuscript Patch</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenManuscriptVersions}>
                    <FileText size={16} />
                    <span>查看 Manuscript Versions</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenVersionLineage}>
                    <GitBranch size={16} />
                    <span>Version Lineage</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={() => {
                      if (selectedPatch?.items[0]) handleOpenPatchItemEditor(selectedPatch, selectedPatch.items[0]);
                      else handleOpenManuscriptPatch();
                    }}
                  >
                    <PenLine size={16} />
                    <span>编辑 Patch Item</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenPatchConflicts}>
                    <GitCompareArrows size={16} />
                    <span>检查 Patch 冲突</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenPatchMerge}>
                    <GitCompareArrows size={16} />
                    <span>合并 Patch 预览</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenManuscriptDiff}>
                    <GitCompareArrows size={16} />
                    <span>查看 Manuscript Diff</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenRevisionLineDiff}>
                    <GitCompareArrows size={16} />
                    <span>精细 Revision Diff</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenRevisionDiffReview}
                    aria-label="Revision Diff Review"
                  >
                    <ShieldCheck size={16} />
                    <span>Revision Diff Review</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenReviewerClosure}
                    aria-label="Reviewer Closure"
                  >
                    <GitCompareArrows size={16} />
                    <span>Reviewer Closure</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenIssueResolution}>
                    <ShieldCheck size={16} />
                    <span>查看 Issue Resolution</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenLiteratureHistory}>
                    <History size={16} />
                    <span>查看文献变更历史</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenLiteratureMetadataDiff}>
                    <BookOpenCheck size={16} />
                    <span>Metadata 字段 Diff</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenLiteratureMetadataBatch}>
                    <BookOpenCheck size={16} />
                    <span>批量审阅 Metadata</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenMetadataReviewWorkflow}
                    aria-label="Metadata Review Workflow"
                  >
                    <BookOpenCheck size={16} />
                    <span>Metadata Review Workflow</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenMetadataRevertPreview}
                    aria-label="Metadata Revert Preview"
                  >
                    <BookOpenCheck size={16} />
                    <span>Metadata Revert Preview</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenPDFQuality}>
                    <FileText size={16} />
                    <span>查看 PDF 质量</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenPDFQualityReport}>
                    <FileText size={16} />
                    <span>PDF 质量报告</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenPDFPageReview}
                    aria-label="PDF Page Review"
                  >
                    <FileText size={16} />
                    <span>PDF Page Review</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenPDFPageTextPreview}
                    aria-label="PDF Page Text Preview"
                  >
                    <FileText size={16} />
                    <span>PDF Page Text Preview</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenReadinessReport}
                    aria-label="v1.0 Readiness"
                  >
                    <ShieldCheck size={16} />
                    <span>v1.0 Readiness</span>
                  </button>
                  <div className="mt-3 text-xs font-black uppercase text-slate-400">Audit-Export</div>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenAuditLog}
                    data-testid="audit-log-entry"
                    aria-label="查看审计日志"
                  >
                    <ScrollText size={16} />
                    <span>查看审计日志</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenAuditVerify}>
                    <ShieldCheck size={16} />
                    <span>验证审计链</span>
                  </button>
                  <button className="secondary-button justify-start" onClick={handleOpenAuditExport}>
                    <ScrollText size={16} />
                    <span>导出 Audit Report</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenAuditFilterExport}
                    aria-label="Audit Filter Export"
                  >
                    <ScrollText size={16} />
                    <span>Audit Filter Export</span>
                  </button>
                  <button
                    className="secondary-button justify-start"
                    onClick={handleOpenRunHistory}
                    data-testid="run-history-entry"
                    aria-label="查看运行历史"
                  >
                    <History size={16} />
                    <span>查看运行历史</span>
                  </button>
                </div>
              </section>
              <Notifications apiOnline={apiOnline} message={message} />
              <section className="panel p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Bot size={19} className="text-[#5b6ee1]" />
                  <h2 className="text-lg font-black">Agent 状态</h2>
                </div>
                <div className="space-y-3 text-sm font-semibold text-slate-600">
                  <div className="flex items-center justify-between">
                    <span>当前步骤</span>
                    <span className="text-slate-950">{project.current_step}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>工作流状态</span>
                    <span className="text-slate-950">{project.workflow_status}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>LLM 模式</span>
                    <span className="text-slate-950">mock fallback</span>
                  </div>
                </div>
              </section>
              <section className="panel p-5">
                <div className="mb-4 flex items-center gap-2">
                  <BrainCircuit size={19} className="text-[#12b5cb]" />
                  <h2 className="text-lg font-black">审计边界</h2>
                </div>
                <div className="space-y-2 text-sm font-semibold leading-6 text-slate-600">
                  <div className="flex gap-2">
                    <Sparkles size={16} className="mt-1 shrink-0 text-[#f59e0b]" />
                    <span>demo、placeholder 和 mock 不会冒充真实科研结论。</span>
                  </div>
                  <div className="flex gap-2">
                    <ShieldCheck size={16} className="mt-1 shrink-0 text-[#18a058]" />
                    <span>Results 只绑定 analysis provenance、figure provenance 和 evidence claim。</span>
                  </div>
                </div>
              </section>
            </aside>
          </div>
        </main>
      </div>

      <OutputDetailDrawer
        open={detailMode === "output"}
        projectId={project.id}
        output={selectedOutput}
        content={outputContent}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <EvidencePanel
        open={detailMode === "evidence"}
        claims={evidence}
        loading={detailLoading}
        onOpenClaimReview={handleOpenEvidenceClaimReview}
        onClose={closeDetails}
      />
      <EvidenceClaimReviewPanel
        open={detailMode === "evidenceClaimReview"}
        claims={evidence}
        reviewState={evidenceClaimReviews}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onReview={handleReviewEvidenceClaim}
        onClose={closeDetails}
      />
      <GlobalTrustDashboard
        open={detailMode === "globalTrust"}
        summary={trustSummary}
        referenceVerificationSummary={referenceVerificationSummary}
        referenceApprovalSummary={referenceApprovalSummary}
        citationGrounding={citationGrounding}
        manuscriptReferencesStatus={manuscriptReferencesStatus}
        loading={detailLoading}
        onOpenReadiness={handleOpenReadinessReport}
        onClose={closeDetails}
      />
      <FigureProvenancePanel
        open={detailMode === "figures"}
        records={figureProvenance}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <ClaimAlignmentPanel
        open={detailMode === "claimAlignment"}
        alignment={claimAlignment}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <SentenceIssuesPanel
        open={detailMode === "sentenceIssues"}
        issues={sentenceIssues}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <RevisionDiffPanel
        open={detailMode === "revisionDiff"}
        issues={sentenceIssues}
        decisions={revisionDecisions}
        loading={detailLoading}
        decisionLoadingId={decisionLoadingId}
        onDecision={handleRevisionDecision}
        onClose={closeDetails}
      />
      <ManuscriptPatchPanel
        open={detailMode === "manuscriptPatch"}
        patches={manuscriptPatches}
        selectedPatch={selectedPatch}
        preview={patchPreview}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onGenerate={handleGenerateManuscriptPatch}
        onSelectPatch={handleSelectPatch}
        onConfirm={handleConfirmPatch}
        onEditItem={handleOpenPatchItemEditor}
        onSafetyCheck={handleSafetyCheckPatchItem}
        onOpenConflicts={handleOpenPatchConflicts}
        onOpenMerge={handleOpenPatchMerge}
        onClose={closeDetails}
      />
      <PatchItemEditorPanel
        open={detailMode === "patchItemEditor"}
        patch={selectedPatch}
        item={selectedPatchItem}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onSave={handleSavePatchItem}
        onSafetyCheck={handleSafetyCheckPatchItem}
        onClose={closeDetails}
      />
      <PatchConflictPanel
        open={detailMode === "patchConflicts"}
        patches={manuscriptPatches}
        report={patchConflictReport}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onCheck={handleCheckPatchConflicts}
        onClose={closeDetails}
      />
      <PatchMergePanel
        open={detailMode === "patchMerge"}
        patches={manuscriptPatches}
        merge={patchMergePreview}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onGenerate={handleGeneratePatchMerge}
        onConfirm={handleConfirmPatchMerge}
        onClose={closeDetails}
      />
      <ManuscriptVersionPanel
        open={detailMode === "manuscriptVersions"}
        history={manuscriptVersions}
        selectedVersion={selectedVersion}
        loading={detailLoading}
        onSelectVersion={handleSelectVersion}
        onOpenDiff={handleGenerateManuscriptDiff}
        onOpenLineage={handleOpenVersionLineage}
        onClose={closeDetails}
      />
      <VersionLineagePanel
        open={detailMode === "versionLineage"}
        lineage={versionLineage}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <ManuscriptDiffPanel
        open={detailMode === "manuscriptDiff"}
        history={manuscriptVersions}
        diffs={manuscriptDiffs}
        selectedDiff={selectedManuscriptDiff}
        preview={manuscriptDiffPreview}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onGenerate={handleGenerateManuscriptDiff}
        onSelectDiff={handleSelectManuscriptDiff}
        onOpenRevisionLineDiff={handleOpenRevisionLineDiff}
        onClose={closeDetails}
      />
      <RevisionLineDiffPanel
        open={detailMode === "revisionLineDiff"}
        history={manuscriptVersions}
        diffs={revisionLineDiffs}
        selectedDiff={selectedRevisionLineDiff}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onGenerate={handleGenerateRevisionLineDiff}
        onSelectDiff={handleSelectRevisionLineDiff}
        onClose={closeDetails}
      />
      <RevisionDiffReviewPanel
        open={detailMode === "revisionDiffReview"}
        diffs={revisionLineDiffs}
        reviewState={revisionDiffReviews}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onReview={handleReviewRevisionDiffChange}
        onClose={closeDetails}
      />
      <ReviewerClosurePanel
        open={detailMode === "reviewerClosure"}
        closure={reviewerClosure}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <LiteratureMetadataPanel
        open={detailMode === "literature"}
        records={literature}
        loading={detailLoading}
        onSave={handleSaveLiterature}
        onClose={closeDetails}
      />
      <LLMSettingsPanel
        open={detailMode === "llmSettings"}
        status={llmStatus}
        promptRegistry={promptRegistry}
        testResult={llmTestResult}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onRefresh={handleRefreshLLMSettings}
        onTest={handleTestLLM}
        onClose={closeDetails}
      />
      <LLMCallLogPanel
        open={detailMode === "llmCallLog"}
        entries={llmCalls}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <LiteratureRAGPanel
        open={detailMode === "literatureRag"}
        index={literatureRagIndex}
        chunks={literatureRagChunks}
        answers={literatureRagAnswers}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onBuild={handleBuildLiteratureRAG}
        onAsk={handleAskLiteratureRAG}
        onClose={closeDetails}
      />
      <RAGQualityPanel
        open={detailMode === "ragQuality"}
        quality={ragChunkQuality}
        evalSet={ragRetrievalEvalSet}
        evaluation={ragRetrievalEvaluation}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onEvaluate={handleEvaluateRAGRetrieval}
        onClose={closeDetails}
      />
      <SourcePassageEvidencePanel
        open={detailMode === "sourcePassageEvidence"}
        report={sourcePassageEvidence}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <LiteratureMetadataLookupPanel
        open={detailMode === "literatureMetadataLookup"}
        result={metadataLookupResults}
        provider={metadataLookupProvider}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onProviderChange={setMetadataLookupProvider}
        onRun={handleRunMetadataLookup}
        onClose={closeDetails}
      />
      <BibTeXPanel
        open={detailMode === "bibtex"}
        data={bibtex}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onGenerate={handleGenerateBibTeX}
        onClose={closeDetails}
      />
      <CitationSupportPanel
        open={detailMode === "citationSupport"}
        report={citationSupport}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <ReferenceVerificationPanel
        open={detailMode === "referenceVerification"}
        results={referenceVerificationResults}
        summary={referenceVerificationSummary}
        provider={referenceVerificationProvider}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onProviderChange={setReferenceVerificationProvider}
        onRun={handleRunReferenceVerification}
        onClose={closeDetails}
      />
      <ReferenceApprovalPanel
        open={detailMode === "referenceApproval"}
        results={referenceVerificationResults}
        approvals={referenceApprovals}
        summary={referenceApprovalSummary}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onDecision={handleReferenceApprovalDecision}
        onClose={closeDetails}
      />
      <VerifiedReferencesPanel
        open={detailMode === "verifiedReferences"}
        status={manuscriptReferencesStatus}
        preview={manuscriptReferencesPreview}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onRefresh={handleRefreshVerifiedReferences}
        onClose={closeDetails}
      />
      <CitationGroundingPanel
        open={detailMode === "citationGrounding"}
        report={citationGrounding}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <LiteratureHistoryPanel
        open={detailMode === "literatureHistory"}
        history={literatureHistory}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <LiteratureMetadataDiffPanel
        open={detailMode === "literatureMetadataDiff"}
        report={literatureMetadataDiff}
        suggestion={literatureMetadataRevertSuggestion}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onSuggestRevert={handleSuggestMetadataRevert}
        onClose={closeDetails}
      />
      <LiteratureMetadataBatchPanel
        open={detailMode === "literatureMetadataBatch"}
        batch={literatureMetadataBatch}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <MetadataReviewWorkflowPanel
        open={detailMode === "metadataReviewWorkflow"}
        diffReport={literatureMetadataDiff}
        reviewState={metadataReviewActions}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onOpenRevertPreview={handleOpenMetadataRevertPreview}
        onReview={handleMetadataReviewAction}
        onClose={closeDetails}
      />
      <MetadataRevertPreviewPanel
        open={detailMode === "metadataRevertPreview"}
        diffReport={literatureMetadataDiff}
        preview={metadataRevertPreview}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onPreview={handleMetadataRevertPreview}
        onClose={closeDetails}
      />
      <PDFQualityPanel
        open={detailMode === "pdfQuality"}
        records={literature}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <PDFQualityReportPanel
        open={detailMode === "pdfQualityReport"}
        report={pdfQualityReport}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <PDFPageReviewPanel
        open={detailMode === "pdfPageReview"}
        report={pdfQualityReport}
        reviewState={pdfPageReviews}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onOpenTextPreview={handleOpenPDFPageTextPreview}
        onReview={handlePDFPageReview}
        onClose={closeDetails}
      />
      <PDFPageTextPreviewPanel
        open={detailMode === "pdfPageTextPreview"}
        preview={pdfPageTextPreview}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <AnalysisProvenancePanel
        open={detailMode === "analysisProvenance"}
        provenance={analysisProvenance}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <StatisticalAssistantPanel
        open={detailMode === "statisticalAssistant"}
        report={statisticalAssistant}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onGenerate={handleGenerateStatisticalAssistant}
        onClose={closeDetails}
      />
      <AnalysisComparePanel
        open={detailMode === "analysisCompare"}
        comparisons={analysisComparisons}
        selectedComparison={selectedAnalysisComparison}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onGenerate={handleGenerateAnalysisCompare}
        onSelectComparison={handleSelectAnalysisComparison}
        onClose={closeDetails}
      />
      <AnalysisTimelinePanel
        open={detailMode === "analysisTimeline"}
        timeline={analysisTimeline}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <AuditLogPanel
        open={detailMode === "auditLog"}
        entries={auditLog}
        loading={detailLoading}
        onOpenExport={handleOpenAuditExport}
        onClose={closeDetails}
      />
      <AuditVerifyPanel
        open={detailMode === "auditVerify"}
        result={auditVerify}
        loading={detailLoading}
        onRefresh={handleRefreshAuditVerify}
        onOpenExport={handleOpenAuditExport}
        onClose={closeDetails}
      />
      <ReadinessReportPanel
        open={detailMode === "readinessReport"}
        report={readinessReport}
        loading={detailLoading}
        onClose={closeDetails}
      />
      <ReleaseReadinessPanel
        open={detailMode === "releaseReadiness"}
        report={readinessReport}
        trustSummary={trustSummary}
        loading={detailLoading}
        onOpenExport={handleOpenProjectExport}
        onRunValidation={handleRunLocalValidation}
        onClose={closeDetails}
      />
      <IssueResolutionPanel
        open={detailMode === "issueResolution"}
        resolution={issueResolution}
        loading={detailLoading}
        reviewLoadingId={issueReviewLoadingId}
        onReview={handleIssueResolutionReview}
        onClose={closeDetails}
      />
      <AuditExportPanel
        open={detailMode === "auditExport"}
        exports={auditExports}
        selectedExport={selectedAuditExport}
        report={auditExportReport}
        manifest={auditFileManifest}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onCreate={handleCreateAuditExport}
        onSelectExport={handleSelectAuditExport}
        onClose={closeDetails}
      />
      <ProjectExportPanel
        open={detailMode === "projectExport"}
        info={projectExport}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onCreate={handleCreateProjectExport}
        onRefresh={handleRefreshProjectExport}
        onClose={closeDetails}
      />
      <AuditFilterExportPanel
        open={detailMode === "auditFilterExport"}
        exports={auditFilteredExports}
        selectedExport={selectedAuditFilteredExport}
        report={auditFilteredExportReport}
        riskLevel={auditFilterRiskLevel}
        loading={detailLoading}
        actionLoading={patchActionLoading}
        onRiskLevelChange={setAuditFilterRiskLevel}
        onCreate={handleCreateAuditFilterExport}
        onSelectExport={handleSelectAuditFilterExport}
        onClose={closeDetails}
      />
      <RunHistoryPanel
        open={detailMode === "runHistory"}
        history={runHistory}
        loading={detailLoading}
        onClose={closeDetails}
      />
    </div>
  );
}
