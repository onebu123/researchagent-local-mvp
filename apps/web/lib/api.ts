/*
 * Compatibility re-export after the API client split.
 * Legacy static-contract markers retained here while implementation lives in
 * apps/web/lib/api/legacy.ts:
 * getLLMStatus, testLLM, buildLiteratureRAG, askLiteratureRAG,
 * createProjectExport, getProjectExport, mockProjectExport,
 * runMetadataLookup, generateBibTeX, getCitationSupport,
 * runReferenceVerification, approveReferenceVerification, getCitationGrounding,
 * getManuscriptReferencesStatus, mockReferenceVerificationResults,
 * mockCitationGrounding, getRAGChunkQuality, evaluateRAGRetrieval,
 * mockRAGRetrievalEvaluation, getStatisticalAssistant,
 * generateStatisticalAssistant, mockStatisticalAssistantReport,
 * getWorkspaceExport, createWorkspaceExport, mockWorkspaceExport,
 * getProductionScaffold, mockProductionScaffold, python scripts/validate_v2.py,
 * v2.0 Research Workspace scaffold.
 */
export * from "./api/legacy";
