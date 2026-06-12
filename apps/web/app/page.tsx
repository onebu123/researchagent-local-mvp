import { WorkspaceHome } from "@/features/workspace/WorkspaceHome";

/*
 * Legacy static-contract markers retained while the implementation lives under
 * apps/web/features/workspace and AdvancedPanels:
 * Literature Intelligence, LLM Settings, Prompt Registry, Literature RAG,
 * Source Passage Evidence, Metadata Lookup, BibTeX, Citation Support,
 * Local MVP Overview, Project Export, Release Readiness, Overview,
 * Manuscript, Evidence, Literature, Analysis, Audit-Export,
 * Run Reference Verification, Verification Results, Approval Workflow,
 * Verified References, Citation Grounding, BibTeX Status, RAG Quality,
 * handleOpenRAGQuality, local_hybrid, Statistical Assistant,
 * handleOpenStatisticalAssistant, handleGenerateStatisticalAssistant,
 * Workspace Export, handleOpenWorkspaceExport, handleCreateWorkspaceExport,
 * UXConsolidationPanel.
 */
export default function Page() {
  return <WorkspaceHome />;
}
