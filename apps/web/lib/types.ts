export type ResourceSummary = {
  literature_count: number;
  dataset_count: number;
  figure_count: number;
  manuscript_count: number;
  review_count: number;
};

export type OutputItem = {
  id: string;
  agent_name: string;
  kind: string;
  title: string;
  relative_path: string;
  mime_type: string;
  created_at: string;
};

export type OutputContent = {
  id: string;
  title: string;
  relative_path: string;
  mime_type: string;
  content: string | Record<string, unknown> | unknown[] | null;
  binary: boolean;
};

export type EvidenceStatus = "supported" | "partial" | "missing" | "needs_human_review";

export type EvidenceClaim = {
  claim_id: string;
  section: string;
  claim: string;
  evidence_type: string;
  data_file: string | null;
  analysis_file: string | null;
  analysis_provenance_file?: string | null;
  figure_file?: string | null;
  figure_provenance_file?: string | null;
  manuscript_file: string | null;
  evidence_status: EvidenceStatus;
  human_verified: boolean;
};

export type EvidenceClaimReviewStatus =
  | "supported"
  | "partially_supported"
  | "unsupported"
  | "needs_more_evidence";

export type EvidenceClaimReview = {
  review_id: string;
  claim_id: string;
  human_status: EvidenceClaimReviewStatus;
  reason: string;
  related_files: string[];
  created_at: string;
  source: string;
  evidence_modified: boolean;
};

export type EvidenceClaimReviewSummaryClaim = {
  claim_id: string;
  section: string | null;
  claim: string | null;
  evidence_type: string | null;
  evidence_status: EvidenceStatus | string | null;
  latest_human_status: EvidenceClaimReviewStatus | null;
  latest_reason: string | null;
  review_count: number;
  related_files: string[];
};

export type EvidenceClaimReviewSummary = {
  generated_at: string;
  relative_path: string;
  summary: {
    total_claims: number;
    reviewed: number;
    supported: number;
    partially_supported: number;
    unsupported: number;
    needs_more_evidence: number;
    unreviewed: number;
  };
  claims: EvidenceClaimReviewSummaryClaim[];
};

export type EvidenceClaimReviewsResponse = {
  reviews: EvidenceClaimReview[];
  summary: EvidenceClaimReviewSummary;
};

export type FigureProvenanceRecord = {
  figure_id: string;
  title: string;
  figure_type: string;
  source_data: string;
  analysis_file?: string;
  script_or_function: string;
  output_files: string[];
  is_ai_generated: boolean;
  is_experimental_result: boolean;
  created_at: string;
  data_hash: string;
  warnings: string[];
};

export type ProjectDetail = {
  id: string;
  name: string;
  domain: string;
  language: string;
  output_format: string;
  workflow_status: string;
  current_step: string;
  created_at: string;
  updated_at: string;
  resources: ResourceSummary;
  latest_outputs: OutputItem[];
};

export type ProjectRead = Omit<ProjectDetail, "resources" | "latest_outputs">;

export type ProjectExportFile = {
  relative_path: string;
  size_bytes: number;
  category: string;
};

export type ProjectExportWarning = {
  relative_path: string;
  reason: string;
};

export type ProjectExportInfo = {
  available: boolean;
  project_id: string;
  created_at?: string;
  export_id?: string;
  file_name?: string;
  relative_path: string | null;
  size_bytes?: number;
  included_file_count?: number | null;
  category_counts: Record<string, number>;
  included_files: ProjectExportFile[];
  warnings: ProjectExportWarning[];
  excluded_patterns?: string[];
  local_mvp_caveats: string[];
  message?: string;
};

export type WorkflowRunResponse = {
  project_id: string;
  workflow_status: string;
  current_step: string;
  outputs: OutputItem[];
  errors: string[];
};

export type ClaimAlignmentRecord = {
  alignment_id: string;
  section: string;
  paragraph_index: number;
  sentence_index: number;
  sentence: string;
  matched_claim_id: string | null;
  match_status: "matched" | "needs_claim_alignment" | "not_claim";
  evidence_status: EvidenceStatus;
  confidence: "high" | "medium" | "low" | string;
  notes: string[];
};

export type ClaimAlignment = {
  manuscript_file: string;
  evidence_file?: string;
  analysis_file?: string;
  figure_provenance_file?: string;
  alignment_status: "complete" | "partial" | "missing" | string;
  aligned_claims: ClaimAlignmentRecord[];
  summary: {
    total_sentences_checked: number;
    matched: number;
    needs_claim_alignment: number;
    not_claim: number;
  };
};

export type SentenceIssue = {
  issue_id: string;
  section: string;
  paragraph_index?: number;
  sentence_index?: number;
  sentence: string;
  issue_type: string;
  severity: "minor" | "major" | "critical" | string;
  related_claim_id: string | null;
  evidence_status?: EvidenceStatus | string;
  suggested_revision: string;
  revision_diff?: RevisionDiff;
};

export type RevisionDiff = {
  can_auto_suggest: boolean;
  before: string;
  after: string;
  change_type:
    | "conservative_rewrite"
    | "remove_overclaim"
    | "add_evidence_note"
    | "mark_as_limitation"
    | "needs_human_rewrite"
    | string;
  preserved_claim_id: string | null;
  preserved_numbers: boolean;
  preserved_units: boolean;
  requires_human_approval: boolean;
  warnings: string[];
};

export type RevisionDecision = {
  decision_id: string;
  issue_id: string;
  decision: "accepted" | "rejected";
  before: string;
  after: string;
  reason: string;
  created_at: string;
  source: "frontend" | "api" | "test" | string;
  applied_to_manuscript: boolean;
};

export type RevisionDecisionPatch = {
  decision: "accepted" | "rejected";
  reason?: string;
};

export type PatchSafetyResult = {
  safe: boolean;
  warnings: string[];
  blocked_reasons: string[];
};

export type PatchManualEdit = {
  edit_id: string;
  old_after: string;
  new_after: string;
  reason: string;
  created_at: string;
  safety_result: PatchSafetyResult;
};

export type ManuscriptPatchItem = {
  patch_item_id: string;
  issue_id: string;
  decision_id: string;
  section: string | null;
  paragraph_index: number | null;
  sentence_index: number | null;
  before: string;
  after: string;
  change_type: string;
  related_claim_id: string | null;
  evidence_status: EvidenceStatus | string | null;
  requires_human_confirmation: boolean;
  warnings: string[];
  item_status?: "safe" | "blocked" | "needs_revision" | "applied" | "skipped" | string;
  manual_edits?: PatchManualEdit[];
  latest_safety_result?: PatchSafetyResult;
};

export type ManuscriptPatchBlockedItem = Partial<ManuscriptPatchItem> & {
  blocked_reasons: string[];
};

export type ManuscriptPatch = {
  patch_id: string;
  source_manuscript: string;
  base_version_id: string;
  created_at: string;
  status: "proposed" | "confirmed" | "rejected" | string;
  source: string;
  items: ManuscriptPatchItem[];
  blocked_items?: ManuscriptPatchBlockedItem[];
  summary: {
    total_items: number;
    safe_to_apply: boolean;
    requires_human_confirmation: boolean;
    blocked_items: number;
    accepted_decisions?: number;
    applied_items?: number;
    skipped_items?: number;
    version_warnings?: string[];
  };
  confirmation?: {
    decision: "confirmed" | "rejected" | string;
    reason: string;
    confirmed_at: string;
    requires_human_confirmation: boolean;
  };
  version_id?: string;
};

export type ManuscriptPatchPreview = {
  patch_id: string;
  relative_path: string;
  content: string;
};

export type ManuscriptPatchConfirmRequest = {
  decision: "confirmed" | "rejected";
  reason?: string;
};

export type ManuscriptPatchItemEditRequest = {
  after: string;
  reason?: string;
};

export type PatchItemSafetyResponse = {
  patch: ManuscriptPatch;
  patch_item: ManuscriptPatchItem;
  safety_result: PatchSafetyResult;
};

export type ManuscriptVersionEntry = {
  version_id: string;
  file: string;
  base_file: string;
  created_at: string;
  source_type?: "patch" | "merge" | string;
  source_patch_id: string | null;
  source_merge_id?: string | null;
  source_patch_ids?: string[];
  source_decision_ids: string[];
  source_issue_ids: string[];
  status: string;
  summary: {
    applied_items: number;
    applied_item_ids?: string[];
    applied_item_refs?: Array<Record<string, unknown>>;
    skipped_items: number;
    skipped_item_details?: Array<Record<string, unknown>>;
    warnings: string[];
  };
};

export type ManuscriptVersionHistory = {
  versions: ManuscriptVersionEntry[];
};

export type ManuscriptVersionContent = {
  version: ManuscriptVersionEntry;
  content: string;
};

export type ManuscriptPatchConfirmResponse = {
  patch: ManuscriptPatch;
  version: ManuscriptVersionEntry | null;
};

export type PatchConflictItemRef = {
  patch_id: string;
  patch_item_id: string;
  issue_id: string;
  related_claim_id?: string | null;
  section: string | null;
  paragraph_index: number | null;
  sentence_index: number | null;
  before: string;
  item_status?: string;
  latest_safety_result?: PatchSafetyResult;
  safety_blocked_reasons?: string[];
};

export type PatchConflict = {
  conflict_id: string;
  conflict_type:
    | "same_sentence"
    | "same_before_text"
    | "overlapping_location"
    | "same_claim"
    | "unsafe_item"
    | string;
  severity: "major" | "minor" | string;
  patch_item_refs: PatchConflictItemRef[];
  message: string;
  resolution_required: boolean;
  suggested_resolution?: string;
};

export type PatchConflictReport = {
  conflict_report_id: string;
  patch_ids: string[];
  created_at: string;
  relative_path: string;
  summary: {
    total_patches: number;
    total_items: number;
    conflicts: number;
    warnings: number;
    major_conflicts: number;
    minor_conflicts: number;
  };
  conflicts: PatchConflict[];
  warnings: string[];
};

export type PatchMergePreview = {
  merge_id: string;
  patch_ids: string[];
  created_at: string;
  source_manuscript: string;
  status: "preview" | "confirmed" | "rejected" | string;
  conflict_report_file: string;
  preview_file: string;
  can_apply: boolean;
  confirmed_at?: string | null;
  rejected_at?: string | null;
  generated_version_id?: string | null;
  generated_diff_id?: string | null;
  confirmed_reason?: string | null;
  rejected_reason?: string | null;
  items: Array<Record<string, unknown>>;
  blocked_items: Array<Record<string, unknown>>;
  summary: {
    total_items: number;
    safe_items: number;
    blocked_items: number;
    conflicts: number;
    major_conflicts: number;
    requires_resolution: boolean;
  };
};

export type PatchMergeConfirmRequest = {
  decision: "confirmed" | "rejected";
  reason?: string;
};

export type PatchMergeConfirmResponse = {
  merge: PatchMergePreview;
  version: ManuscriptVersionEntry | null;
  diff: ManuscriptDiff | null;
};

export type ManuscriptDiffHunk = {
  hunk_id: string;
  old_start: number;
  old_lines: number;
  new_start: number;
  new_lines: number;
  removed: string[];
  added: string[];
  related_issue_ids: string[];
  related_claim_ids: string[];
};

export type ManuscriptDiff = {
  diff_id: string;
  base_file: string;
  version_id: string;
  version_file: string;
  created_at: string;
  relative_path: string;
  preview_file: string;
  summary: {
    added_lines: number;
    removed_lines: number;
    changed_hunks: number;
  };
  hunks: ManuscriptDiffHunk[];
};

export type ManuscriptDiffPreview = {
  diff_id: string;
  relative_path: string;
  content: string;
};

export type RevisionLineDiffChange = {
  change_id: string;
  section: string;
  paragraph_index: number;
  sentence_index: number;
  line_start: number;
  line_end: number;
  before: string;
  after: string;
  change_type: string;
  related_issue_ids: string[];
  related_claim_ids: string[];
  safety_status: "safe" | "needs_human_review" | string;
  notes: string[];
};

export type RevisionLineDiff = {
  revision_diff_id: string;
  base_file: string;
  target_file: string;
  created_at: string;
  relative_path: string;
  summary: {
    sections_checked: number;
    paragraphs_checked: number;
    sentences_changed: number;
    lines_changed: number;
    issues_linked: number;
    claims_linked: number;
  };
  changes: RevisionLineDiffChange[];
};

export type IssueResolutionVersion = {
  version_id: string;
  source_type?: "patch" | "merge" | string;
  source_merge_id?: string | null;
  source_patch_ids: string[];
  resolved_issue_ids: string[];
  unresolved_issue_ids: string[];
  partially_resolved_issue_ids: string[];
  notes: string[];
  human_review_summary?: {
    reviewed: number;
    resolved: number;
    unresolved: number;
    needs_review: number;
  };
  latest_human_reviews?: IssueResolutionReview[];
};

export type IssueResolution = {
  generated_at: string;
  versions: IssueResolutionVersion[];
  summary: {
    total_sentence_issues: number;
    resolved: number;
    unresolved: number;
    partially_resolved: number;
    human_reviews?: number;
    latest_human_status_counts?: Record<string, number>;
  };
  notes: string[];
  review_history?: IssueResolutionReview[];
};

export type IssueResolutionReview = {
  review_id: string;
  issue_id: string;
  version_id: string;
  auto_status: string;
  human_status: "resolved" | "unresolved" | "needs_review";
  reason: string;
  created_at: string;
  source: string;
};

export type IssueResolutionReviewRequest = {
  version_id: string;
  human_status: "resolved" | "unresolved" | "needs_review";
  reason?: string;
};

export type VersionLineageNode = {
  id: string;
  type: "manuscript" | "patch" | "merge" | "version" | "diff" | "issue_resolution" | string;
  label: string;
  file?: string;
  status?: string;
  source_type?: string;
  source?: string;
  can_apply?: boolean;
  generated_version_id?: string | null;
  generated_diff_id?: string | null;
  summary?: Record<string, unknown>;
};

export type VersionLineageEdge = {
  source: string;
  target: string;
  relation: string;
};

export type VersionLineage = {
  generated_at: string;
  relative_path: string;
  nodes: VersionLineageNode[];
  edges: VersionLineageEdge[];
  summary: {
    nodes: number;
    edges: number;
    versions: number;
    patches: number;
    merges: number;
    diffs: number;
  };
  warnings: string[];
};

export type AuditVerifyResult = {
  valid: boolean;
  checked_entries: number;
  first_invalid_index: number | null;
  errors: string[];
};

export type LiteratureMetadataStatus = "placeholder" | "extracted" | "verified";

export type LiteratureRecord = {
  literature_id: string;
  source_file: string;
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  journal?: string | null;
  source_type: "pdf" | "markdown" | "txt";
  parsed_text_file: string;
  parse_metadata_file?: string | null;
  parse_status: string;
  metadata_status: LiteratureMetadataStatus;
  human_verified: boolean;
  warnings: string[];
  page_count?: number | null;
  empty_page_count?: number | null;
  pages?: PDFPageQuality[];
  quality_score?: number | null;
  quality_label?: string | null;
  needs_manual_review?: boolean | null;
  reference_verification_status?: "approved" | "rejected" | "needs_manual_check" | string | null;
  reference_verification_id?: string | null;
};

export type PDFPageQuality = {
  page_number: number;
  char_count: number;
  empty: boolean;
  warnings: string[];
  quality_signal: "good" | "medium" | "low" | "empty" | string;
  ocr: {
    ocr_attempted: boolean;
    ocr_engine: string | null;
    ocr_status: "not_configured" | string;
    ocr_text_file: string | null;
  };
};

export type LiteraturePatch = Partial<
  Pick<
    LiteratureRecord,
    "title" | "authors" | "year" | "doi" | "journal" | "metadata_status" | "human_verified"
  >
>;

export type LiteratureHistoryEntry = {
  history_id: string;
  literature_id: string;
  changed_fields: string[];
  old_values: Record<string, unknown>;
  new_values: Record<string, unknown>;
  changed_at: string;
  source: string;
  reason: string;
};

export type LiteratureMetadataFieldChange = {
  field: string;
  old_value: unknown;
  new_value: unknown;
  change_type: "added" | "modified" | "removed" | "unchanged" | string;
  source_history_id: string | null;
  revert_suggestion: {
    can_revert: boolean;
    revert_to: unknown;
    warning: string;
  };
};

export type LiteratureMetadataDiffRecord = {
  literature_id: string;
  source_file?: string | null;
  title?: string | null;
  changes: LiteratureMetadataFieldChange[];
  summary: {
    added: number;
    modified: number;
    removed: number;
  };
};

export type LiteratureMetadataDiffReport = {
  generated_at: string;
  relative_path: string;
  records: LiteratureMetadataDiffRecord[];
};

export type LiteratureMetadataRevertSuggestion = LiteratureMetadataFieldChange & {
  literature_id: string;
  applied: boolean;
  literature_index_modified: boolean;
};

export type MetadataRevertPreview = {
  preview_id: string;
  generated_at: string;
  relative_path: string;
  literature_id: string;
  field: string;
  source_history_id: string;
  current_value: unknown;
  revert_to: unknown;
  history_new_value: unknown;
  would_change: boolean;
  safe_to_apply: boolean;
  conflicts: Array<{
    field: string;
    severity: string;
    message: string;
  }>;
  applied: boolean;
  literature_index_modified: boolean;
  notes: string[];
};

export type LiteratureMetadataBatchRecord = {
  literature_id: string;
  title: string | null;
  metadata_status: LiteratureMetadataStatus;
  human_verified: boolean;
  recommended_action: string;
  reasons: string[];
};

export type LiteratureMetadataBatchReview = {
  batch_id: string;
  created_at: string;
  relative_path: string;
  source_index: string;
  literature_index_modified: boolean;
  summary: {
    total_records: number;
    placeholder: number;
    extracted: number;
    verified: number;
    needs_review: number;
  };
  records: LiteratureMetadataBatchRecord[];
};

export type AnalysisProvenance = {
  analysis_id: string;
  input_data_file: string;
  input_data_hash: string;
  analysis_function: string;
  generated_files: string[];
  parameters?: Record<string, string | boolean | number | null>;
  script_version?: Record<string, string>;
  random_seed?: number | null;
  random_seed_note?: string;
  output_file_hashes?: Record<string, string>;
  created_at: string;
  runtime: {
    python_version?: string;
    pandas_version?: string;
    numpy_version?: string;
  };
  row_count: number;
  column_count: number;
  warnings: string[];
  limitations: string[];
  is_demo_data?: boolean;
};

export type StatisticalAssistantVariableRole = {
  column: string;
  dtype: string;
  role_suggestions: string[];
  reasons: string[];
};

export type StatisticalAssistantDescriptiveCard = {
  column: string;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  missing_count: number;
  recommended_visualization: string;
  notes: string[];
};

export type StatisticalAssistantCorrelationItem = {
  x: string;
  y: string;
  correlation: number;
  association_strength: string;
  recommendation: string;
  limitations: string[];
};

export type StatisticalAssistantMethodSuggestion = {
  method: string;
  status: string;
  reason: string;
  outputs: string[];
};

export type StatisticalAssistantReport = {
  report_id: string;
  generated_at: string;
  relative_path: string;
  source_files: {
    summary: string;
    processed_data: string;
  };
  dataset: {
    row_count: number;
    column_count: number;
    columns: string[];
    numeric_columns: string[];
    categorical_columns: string[];
    is_demo_data: boolean;
  };
  data_health: {
    missingness: Array<{
      column: string;
      missing_count: number;
      missing_rate: number;
      severity: string;
    }>;
    missing_value_columns: number;
    constant_columns: string[];
    near_constant_columns: Array<Record<string, unknown>>;
    outlier_flags: Array<Record<string, unknown>>;
    outlier_flagged_columns: number;
    small_sample_warning: boolean;
    warnings: string[];
  };
  variable_roles: StatisticalAssistantVariableRole[];
  descriptive_cards: StatisticalAssistantDescriptiveCard[];
  correlation_review: StatisticalAssistantCorrelationItem[];
  method_suggestions: StatisticalAssistantMethodSuggestion[];
  guardrails: string[];
  limitations: string[];
};

export type PDFQualityReportRecord = {
  source_file: string;
  metadata_file: string;
  quality_label: string;
  quality_score: number;
  page_count: number;
  low_quality_pages: number[];
  empty_pages: number[];
  suspected_scanned_pages: number[];
  issue_categories: Record<string, number>;
  recommended_action: string;
  ocr_attempted: boolean;
  warnings: string[];
};

export type PDFQualityReport = {
  generated_at: string;
  relative_path: string;
  pdfs: PDFQualityReportRecord[];
  summary: {
    pdf_count: number;
    low_quality_pdf_count: number;
    pages_requiring_review: number;
  };
};

export type AnalysisCompareFieldDiff = {
  field?: string;
  change_type: "added" | "modified" | "removed" | string;
  base: unknown;
  target: unknown;
};

export type AnalysisComparison = {
  comparison_id: string;
  base_provenance: string;
  target_provenance: string;
  created_at: string;
  relative_path: string;
  summary: {
    parameters_changed: number;
    input_hash_changed: boolean;
    output_hash_changes: number;
    runtime_changes: number;
    warnings_changed: number;
    limitations_changed: number;
  };
  diffs: {
    parameters: AnalysisCompareFieldDiff[];
    input_data_hash: {
      base: unknown;
      target: unknown;
      changed: boolean;
    };
    output_file_hashes: AnalysisCompareFieldDiff[];
    runtime: AnalysisCompareFieldDiff[];
    warnings: AnalysisCompareFieldDiff[];
    limitations: AnalysisCompareFieldDiff[];
  };
};

export type AuditLogEntry = {
  audit_id: string;
  event_type: string;
  event_category?: string;
  risk_level?: string;
  entity_type?: string;
  entity_id?: string | null;
  project_id: string;
  timestamp: string;
  source: string;
  actor: {
    type: string;
    id: string;
  };
  summary: string;
  details: Record<string, unknown>;
  prev_hash?: string;
  entry_hash?: string;
};

export type AuditExportSummary = {
  export_id: string;
  created_at: string;
  entry_count: number;
  hash_chain_valid: boolean;
  source_file: string;
  report_file: string;
  manifest_file?: string;
};

export type AuditExport = AuditExportSummary & {
  first_invalid_index: number | null;
  entries: AuditLogEntry[];
};

export type AuditExportReport = {
  export_id: string;
  relative_path: string;
  content: string;
};

export type AuditFileManifestRecord = {
  relative_path: string;
  category: string;
  size_bytes: number;
  sha256: string;
};

export type AuditFileManifest = {
  manifest_id: string;
  project_id: string;
  export_id: string;
  created_at: string;
  relative_path: string;
  file_count: number;
  category_counts: Record<string, number>;
  files: AuditFileManifestRecord[];
  warnings: string[];
  notes: string[];
};

export type RunHistoryEntry = {
  run_id: string;
  run_type: "workflow" | "step" | string;
  step: string | null;
  status: "completed" | "failed" | "running" | string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  outputs: string[];
  errors: string[];
  warnings: string[];
  failure_diagnostics: {
    error_type: string | null;
    error_message: string | null;
    failed_step: string | null;
    likely_cause: string | null;
    suggested_recovery: string[];
  };
  recoverable: boolean;
  retry_hint: "rerun_step" | "rerun_workflow" | "manual_fix_required" | null | string;
  is_fixture?: boolean;
};

export type RunHistory = {
  runs: RunHistoryEntry[];
};

export type RevisionDiffHumanStatus =
  | "accepted"
  | "rejected"
  | "needs_rewrite"
  | "needs_evidence";

export type RevisionDiffReview = {
  review_id: string;
  revision_diff_id: string;
  change_id: string;
  human_status: RevisionDiffHumanStatus;
  reason: string;
  created_at: string;
  source: string;
};

export type RevisionDiffReviewSummaryChange = Pick<
  RevisionLineDiffChange,
  "change_id" | "before" | "after" | "related_issue_ids" | "related_claim_ids"
> & {
  revision_diff_id: string;
  latest_human_status: RevisionDiffHumanStatus | null;
  latest_reason: string | null;
  review_count: number;
};

export type RevisionDiffReviewSummary = {
  generated_at: string;
  relative_path: string;
  summary: {
    total_changes: number;
    reviewed: number;
    accepted: number;
    rejected: number;
    needs_rewrite: number;
    needs_evidence: number;
    unreviewed: number;
  };
  changes: RevisionDiffReviewSummaryChange[];
};

export type RevisionDiffReviewsResponse = {
  reviews: RevisionDiffReview[];
  summary: RevisionDiffReviewSummary;
};

export type MetadataReviewActionValue =
  | "accept_change"
  | "reject_change"
  | "needs_verification"
  | "request_revert";

export type MetadataReviewAction = {
  action_id: string;
  review_action_id?: string;
  literature_id: string;
  field: string;
  action: MetadataReviewActionValue;
  source_history_id: string;
  reason: string;
  created_at: string;
  source: string;
  literature_index_modified?: boolean;
};

export type MetadataReviewSummary = {
  generated_at: string;
  relative_path: string;
  summary: {
    total_actions: number;
    accept_change: number;
    reject_change: number;
    needs_verification: number;
    request_revert: number;
  };
  records: Array<{
    literature_id: string;
    field: string;
    latest_action: MetadataReviewActionValue | null;
    review_count: number;
    latest_reason: string | null;
    source_history_id: string | null;
  }>;
};

export type MetadataReviewActionsResponse = {
  actions: MetadataReviewAction[];
  summary: MetadataReviewSummary;
};

export type PDFPageReviewStatus =
  | "accepted_as_readable"
  | "needs_ocr"
  | "ignore_page"
  | "needs_manual_check";

export type PDFPageReview = {
  review_id: string;
  page_review_id?: string;
  source_file: string;
  page_number: number;
  auto_quality_signal: string;
  human_status: PDFPageReviewStatus;
  reason: string;
  created_at: string;
  source: string;
  ocr_attempted: boolean;
};

export type PDFPageReviewSummary = {
  generated_at: string;
  relative_path: string;
  summary: {
    total_reviews: number;
    accepted_as_readable: number;
    needs_ocr: number;
    ignore_page: number;
    needs_manual_check: number;
  };
  pages: Array<{
    source_file: string;
    page_number: number;
    auto_quality_signal: string;
    latest_human_status: PDFPageReviewStatus | null;
    latest_reason: string | null;
    review_count: number;
  }>;
};

export type PDFPageReviewsResponse = {
  reviews: PDFPageReview[];
  summary: PDFPageReviewSummary;
};

export type PDFPageTextPreviewPage = {
  source_file: string;
  literature_id: string | null;
  page_number: number;
  char_count: number;
  text_preview: string;
  parse_status: string;
  auto_quality_signal: string;
  human_status: PDFPageReviewStatus | "unreviewed" | string;
  ocr_attempted: boolean;
  warnings: string[];
};

export type PDFPageTextPreviewResponse = {
  generated_at: string;
  relative_path: string;
  summary: {
    pdf_count: number;
    page_count: number;
    ocr_attempted: boolean;
  };
  pages: PDFPageTextPreviewPage[];
  notes: string[];
};

export type AnalysisTimeline = {
  generated_at: string;
  relative_path: string;
  timeline: Array<{
    timeline_id: string;
    run_id: string | null;
    analysis_provenance: string;
    comparison_ids: string[];
    comparisons?: AnalysisComparison[];
    created_at: string;
    summary: Record<string, unknown>;
  }>;
  unlinked_comparisons: AnalysisComparison[];
  change_summary?: {
    runs_total: number;
    failed_runs: number;
    comparisons_total: number;
    comparisons_with_changes: number;
    parameter_changes_total: number;
    input_hash_changes_total: number;
    output_hash_changes_total: number;
    warning_changes_total: number;
  };
  failed_run_diagnostics?: Array<{
    run_id: string | null;
    run_type: string | null;
    step: string | null;
    failed_step: string | null;
    error_type: string | null;
    error_message: string | null;
    likely_cause: string | null;
    suggested_recovery: string[];
    recoverable: boolean | null;
    retry_hint: string | null;
    is_fixture: boolean;
  }>;
  summary: {
    runs: number;
    comparisons: number;
    changes_detected: number;
    failed_runs?: number;
  };
};

export type ReviewerClosureIssue = {
  issue_id: string;
  issue_type: string | null;
  severity: string | null;
  sentence: string | null;
  closure_status:
    | "closed"
    | "open"
    | "unlinked"
    | "needs_evidence"
    | "needs_rewrite"
    | "rejected"
    | string;
  linked_changes: Array<{
    revision_diff_id: string;
    change_id: string;
    before?: string | null;
    after?: string | null;
  }>;
  latest_revision_review: RevisionDiffReview | null;
  reason: string;
};

export type ReviewerClosureSummary = {
  generated_at: string;
  relative_path: string;
  summary: {
    total_sentence_issues: number;
    closed: number;
    open: number;
    unlinked: number;
    needs_evidence: number;
    needs_rewrite: number;
    rejected: number;
  };
  issues: ReviewerClosureIssue[];
  notes: string[];
};

export type TrustItem = {
  item_type: string;
  item_id: string | null;
  status: string | null;
  message: string;
};

export type TrustSummary = {
  generated_at: string;
  relative_path: string;
  overall_status: string;
  scores: Record<string, number>;
  counts: Record<string, number>;
  audit_hash_chain: AuditVerifyResult;
  failed_run_diagnostics: Array<{
    run_id: string | null;
    failed_step: string | null;
    likely_cause: string | null;
    suggested_recovery: string[];
    is_fixture: boolean;
  }>;
  open_items: TrustItem[];
  blocking_issues: TrustItem[];
  source_files: Record<string, string | null>;
  notes: string[];
};

export type ReadinessReport = {
  report_id: string;
  generated_at: string;
  relative_path: string;
  readiness_level: string;
  local_mvp_checks: Record<string, boolean>;
  trust_overall_status: string | null;
  blocking_gaps: string[];
  production_gaps: string[];
  recommended_next_steps: string[];
  notes: string[];
};

export type AuditFilteredExportRequest = {
  event_category?: string;
  risk_level?: string;
  entity_type?: string;
  entity_id?: string;
};

export type AuditFilteredExportSummary = {
  export_id: string;
  created_at: string;
  source_file: string;
  report_file: string;
  filters: Record<string, string>;
  matching_entry_count: number;
};

export type AuditFilteredExport = AuditFilteredExportSummary & {
  entries: AuditLogEntry[];
  warnings: string[];
};

export type AuditFilteredExportReport = {
  export_id: string;
  relative_path: string;
  content: string;
};

export type LLMStatus = {
  mode: string;
  effective_mode: string;
  provider: string;
  model: string;
  base_url_host: string;
  api_key_configured: boolean;
  timeout_seconds: number;
  max_retries: number;
};

export type LLMTestResult = {
  ok: boolean;
  content: unknown;
  raw_content: string;
  mode: string;
  provider: string;
  model: string;
  prompt_version: string;
  status: string;
  usage: Record<string, unknown>;
  error: string | null;
};

export type PromptRegistryItem = {
  prompt_version: string;
  file_name: string;
  purpose: string;
  content_sha256: string;
  char_count: number;
};

export type PromptRegistry = {
  prompts: PromptRegistryItem[];
  count: number;
  required_prompt_versions: string[];
};

export type LLMCallLogEntry = {
  call_id: string;
  created_at: string;
  project_id: string;
  operation: string;
  provider: string;
  model: string;
  mode: string;
  prompt_version: string;
  status: string;
  request_summary: Record<string, unknown>;
  response_summary: Record<string, unknown>;
  usage: Record<string, unknown>;
  error: string | null;
  attempts: number;
  metadata: Record<string, unknown>;
};

export type RAGSourcePassage = {
  chunk_id: string;
  literature_id: string;
  source_file: string | null;
  title: string | null;
  metadata_status: string | null;
  human_verified: boolean;
  score?: number;
  score_breakdown?: {
    keyword_score: number;
    ngram_score: number;
    metadata_trust_score: number;
    quality_score: number;
  };
  matched_terms?: string[];
  quality_warnings?: string[];
  text: string;
};

export type LiteratureRAGIndex = {
  project_id: string;
  created_at: string;
  relative_path: string;
  chunks_file: string;
  retrieval_mode: string;
  supported_retrieval_modes?: string[];
  optional_paperqa2_enabled: boolean;
  prompt_version: string;
  chunk_count: number;
  literature_count: number;
  notes: string[];
};

export type RAGChunkQualityItem = {
  chunk_id: string;
  literature_id: string;
  source_file: string | null;
  title: string | null;
  metadata_status: string | null;
  human_verified: boolean;
  character_count: number;
  token_count: number;
  lexical_diversity: number;
  quality_score: number;
  quality_status: "ok" | "needs_review" | "poor" | string;
  warnings: string[];
};

export type RAGChunkQualityReport = {
  generated_at: string;
  relative_path: string;
  chunks_file: string;
  summary: Record<string, number>;
  items: RAGChunkQualityItem[];
  limitations: string[];
};

export type RAGRetrievalEvalCase = {
  case_id: string;
  query: string;
  expected_literature_id: string;
  expected_chunk_id: string;
  source: string;
  notes: string[];
};

export type RAGRetrievalEvalSet = {
  generated_at: string;
  relative_path: string;
  retrieval_mode: string;
  cases: RAGRetrievalEvalCase[];
  limitations: string[];
};

export type RAGRetrievalEvalResult = {
  case_id: string;
  query: string;
  expected_chunk_id: string;
  expected_literature_id: string;
  top_chunk_ids: string[];
  top_literature_ids: string[];
  hit_at_1: boolean;
  hit_at_3: boolean;
  rank: number | null;
  top_score: number;
  top_score_breakdown: {
    keyword_score: number;
    ngram_score: number;
    metadata_trust_score: number;
    quality_score: number;
  };
};

export type RAGRetrievalEvalReport = {
  generated_at: string;
  relative_path: string;
  eval_set_file: string;
  retrieval_mode: string;
  metrics: Record<string, number>;
  results: RAGRetrievalEvalResult[];
  limitations: string[];
};

export type LiteratureRAGChunk = RAGSourcePassage & {
  parsed_text_file: string | null;
  source_type: string | null;
  start_char: number;
  end_char: number;
  token_count: number;
  tokens: string[];
  chunk_hash: string;
};

export type LiteratureRAGAnswer = {
  answer_id: string;
  created_at: string;
  project_id: string;
  question: string;
  answer: string;
  source_passages: RAGSourcePassage[];
  unsupported_notes: string[];
  limitations: string[];
  retrieval: Record<string, unknown>;
  llm: {
    mode: string;
    provider: string;
    model: string;
    prompt_version: string;
    status: string;
  };
};

export type SourcePassageEvidenceRecord = {
  evidence_id: string;
  answer_id: string;
  question: string | null;
  chunk_id: string;
  literature_id: string | null;
  source_file: string | null;
  title: string | null;
  metadata_status: string;
  human_verified: boolean;
  support_status: "supported" | "partial" | "needs_human_review" | string;
  excerpt: string;
  notes: string[];
};

export type SourcePassageEvidenceReport = {
  generated_at: string;
  relative_path: string;
  source_chunks_file: string;
  source_answers_file: string;
  records: SourcePassageEvidenceRecord[];
  summary: Record<string, number>;
};

export type LiteratureMetadataLookupRecord = {
  lookup_id: string;
  created_at: string;
  provider: string;
  literature_id: string;
  source_file: string | null;
  query_title: string | null;
  candidates: Array<Record<string, unknown>>;
  status: string;
  human_verification_required: boolean;
  literature_index_modified: boolean;
  warnings: string[];
  prompt_version: string;
};

export type LiteratureMetadataLookupResponse = {
  results: LiteratureMetadataLookupRecord[];
  summary: Record<string, unknown>;
};

export type BibTeXResponse = {
  bibtex: string;
  report: {
    generated_at: string;
    relative_path: string;
    bibtex_file: string;
    prompt_version: string;
    formal_entries: number;
    approved_entries?: number;
    candidate_records?: number;
    rejected_records?: number;
    placeholder_records?: number;
    skipped_records: number;
    written: Array<Record<string, unknown>>;
    skipped: Array<Record<string, unknown>>;
    candidates?: Array<Record<string, unknown>>;
    rejected?: Array<Record<string, unknown>>;
    placeholders?: Array<Record<string, unknown>>;
    warnings: string[];
  };
};

export type CitationSupportRecord = {
  claim_id: string;
  claim: string;
  status: "supported" | "partial" | "unsupported" | "needs_human_review" | string;
  matched_chunk_ids: string[];
  overlap_terms: number;
  source_passage_evidence_ids: string[];
  notes: string[];
};

export type CitationSupportReport = {
  generated_at: string;
  relative_path: string;
  prompt_version: string;
  source_chunks_file: string;
  source_passage_evidence_file: string;
  records: CitationSupportRecord[];
  summary: Record<string, number>;
  limitations: string[];
};

export type ReferenceVerificationProvider =
  | "mock_fixture"
  | "crossref_optional"
  | "semantic_scholar_optional"
  | "pubmed_optional";

export type ReferenceMatchScores = {
  title_match_score: number;
  author_match_score: number;
  year_match: "match" | "mismatch" | "missing" | string;
  doi_match: "match" | "mismatch" | "missing" | string;
  journal_match_score: number;
  overall_confidence: number;
};

export type ReferenceVerificationResult = {
  verification_id: string;
  literature_id: string;
  provider: ReferenceVerificationProvider | string;
  query: Record<string, unknown>;
  candidate: Record<string, unknown>;
  match_scores: ReferenceMatchScores;
  status: string;
  verification_status: string;
  requires_human_approval: boolean;
  applied_to_literature_index: boolean;
  warnings: string[];
  error: string | null;
  created_at: string;
};

export type ReferenceVerificationSummaryResponse = {
  generated_at: string;
  total: number;
  total_records: number;
  summary: Record<string, number>;
  providers: Record<string, number>;
};

export type ReferenceVerificationRunResponse = {
  results: ReferenceVerificationResult[];
  summary: ReferenceVerificationSummaryResponse;
  literature_index_modified: boolean;
};

export type ReferenceApprovalDecision = "approved" | "rejected" | "needs_manual_check";

export type ReferenceApproval = {
  approval_id: string;
  verification_id: string;
  literature_id: string;
  decision: ReferenceApprovalDecision | string;
  reason: string;
  approved_metadata: Record<string, unknown>;
  created_at: string;
  source: string;
  apply_to_literature_index: boolean;
  applied_to_literature_index: boolean;
};

export type ReferenceApprovalSummaryResponse = {
  generated_at: string;
  relative_path: string;
  summary: Record<string, number>;
  latest_by_literature: Record<string, ReferenceApproval>;
};

export type ReferenceApprovalResponse = ReferenceApproval & {
  literature_index_modified: boolean;
  summary: ReferenceApprovalSummaryResponse;
  applied_record: Record<string, unknown> | null;
};

export type CitationGroundingItem = {
  grounding_id: string;
  claim_id: string;
  claim: string;
  candidate_chunk_id: string | null;
  literature_id: string | null;
  source_file: string | null;
  text_excerpt: string;
  grounding_strength: "strong" | "moderate" | "weak" | "unsupported" | "needs_human_review" | string;
  signals: Record<string, unknown>;
  limitations: string[];
  requires_human_review: boolean;
};

export type CitationGroundingReport = {
  generated_at: string;
  relative_path: string;
  items: CitationGroundingItem[];
  summary: Record<string, number>;
};

export type ManuscriptReferenceRecord = {
  literature_id: string;
  title: string | null;
  authors: string[];
  year: number | null;
  doi: string | null;
  journal: string | null;
  source_file: string | null;
  metadata_status: string | null;
  reference_verification_status: string | null;
  reference_verification_id: string | null;
  human_verified: boolean;
  warning?: string;
  verification_results?: ReferenceVerificationResult[];
};

export type ManuscriptReferencesStatus = {
  generated_at: string;
  relative_path: string;
  preview_file: string;
  verified_references: ManuscriptReferenceRecord[];
  candidate_references: ManuscriptReferenceRecord[];
  placeholder_records: ManuscriptReferenceRecord[];
  warnings: string[];
};

export type ManuscriptReferencesPreview = {
  relative_path: string;
  content: string;
};
