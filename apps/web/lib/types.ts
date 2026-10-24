export type Research = {
  id: string;
  display_id: string;
  title: string;
  type: string;
  status: "draft" | "in-review" | "approved" | "archived" | "rejected";
  collection_method: string;
  summary: string | null;
  content: string;
  source_url: string | null;
  authors: string[];
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
};

export type ResearchList = { items: Research[]; total: number; page: number; page_size: number };

export type Provider = {
  id: string;
  configured: boolean;
  reachable: boolean | null;
  active: boolean;
  chat_active?: boolean;
  model: string;
};

export type SourceKind = "github" | "facebook" | "paper" | "pdf" | "article";

export type NormalizedSource = {
  source_type?: SourceKind;
  canonical_url?: string;
  authors?: string[];
  published_at?: string | null;
  description?: string;
  collection_status?: "EXTRACTED" | "PARTIAL";
  limitation_code?: string | null;
  limitation_message?: string | null;
  metadata?: Record<string, unknown>;
};

export type SourceSubmission = {
  id: string;
  url: string;
  source_type: string;
  status: "pending" | "processing" | "fetching" | "extracting" | "analyzing" | "completed" | "partial_success" | "failed";
  stage: string;
  review_status: "not_requested" | "needs_review" | "approved" | "rejected" | "duplicate";
  title: string | null;
  content_preview: string;
  classification: {
    confidence?: number;
    relevance_score?: number;
    summary?: string;
    technologies?: string[];
    business_domains?: string[];
    normalized_source?: NormalizedSource;
  };
  transcript: {
    configured: boolean;
    language: string | null;
    segment_count: number;
    updated_at: string | null;
  };
  provider_name: string | null;
  model_name: string | null;
  attempt_count: number;
  next_attempt_at: string | null;
  error: string | null;
  error_code: string | null;
  error_details: Record<string, unknown>;
  research_id: string | null;
  duplicate_of_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type ReviewBacklog = {
  needs_review: number;
  approved: number;
  rejected: number;
  duplicate: number;
  not_requested: number;
  failed: number;
  duplicates_awaiting_original: number;
  auto_approve_confidence: number;
};

export type TranscriptSegment = {
  timestamp_seconds: number;
  text: string;
};

export type DocumentWorkspace = {
  id: string;
  research_id: string;
  attachment_id: string;
  filename: string;
  summary: string;
  mime_type: string;
  size_bytes: number;
  content_hash: string;
  processing_status: string;
  review_status: string;
  extraction_limitations: Array<Record<string, unknown>>;
  error_code: string | null;
  error_message: string | null;
  provider_name: string | null;
  model_name: string | null;
  attempt_count: number;
  next_attempt_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  extracted_char_count: number;
  graph_node_count: number;
  graph_edge_count: number;
  source_version: number;
  editable: boolean;
  rag_status: string;
  rag_chunk_count: number;
  rag_indexed_version: number | null;
  rag_error_code: string | null;
  rag_indexed_at: string | null;
  evaluation: PaperEvaluation | null;
  created_at: string;
  updated_at: string;
};

export type DocumentWorkspaceList = { items: DocumentWorkspace[]; total: number };

export type DocumentContent = {
  workspace_id: string;
  filename: string;
  format: string;
  preview_kind: "markdown" | "latex" | "markup" | "html" | "docx" | "pdf" | "plain";
  source_text: string | null;
  extracted_text: string;
  supports_raw: boolean;
  source_truncated: boolean;
  editable: boolean;
  source_version: number;
  editing_representation?: "source" | "extracted_text";
  original_available?: boolean;
  original_preview_kind?: "pdf" | null;
};

export type DocumentSourceVersion = {
  id: string;
  version_number: number;
  content_hash: string;
  size_bytes: number;
  origin: string;
  change_summary: string | null;
  created_by: string;
  created_at: string;
  current: boolean;
};

export type DocumentSourceVersionList = {
  items: DocumentSourceVersion[];
  total: number;
};

export type DocumentAIEdit = {
  id: string;
  workspace_id: string;
  base_version: number;
  selection_start: number;
  selection_end: number;
  action: string;
  instruction: string | null;
  original_text: string;
  replacement_text: string;
  explanation: string;
  provider_name: string;
  model_name: string;
  status: string;
  accepted_version_number: number | null;
  created_at: string;
};

export type DocumentRagStatus = {
  status: string;
  chunk_count: number;
  indexed_version: number | null;
  error_code: string | null;
  indexed_at: string | null;
};

export type DocumentBrainstormMessage = {
  role: "user" | "assistant";
  content: string;
};

export type DocumentBrainstormResponse = {
  content: string;
  provider_name: string;
  model_name: string;
  source_context_truncated: boolean;
};

export type DocumentInstantEditAction =
  | "improve"
  | "shorten"
  | "expand"
  | "fix_grammar"
  | "tone"
  | "translate"
  | "bullets"
  | "table"
  | "custom";

export type DocumentInstantEditPatch = {
  source_revision: string;
  selection_start: number;
  selection_end: number;
  original_text_hash: string;
  replacement_text: string;
  explanation: string;
  risk: "low" | "medium" | "high";
  auto_apply_allowed: boolean;
  warnings: string[];
  provider_name: string;
  model_name: string;
};

export type PaperEvaluation = {
  id: string;
  rubric_version: string;
  dimension_scores: Record<string, number>;
  fit_score: number | null;
  decision: "hard_gate_failed" | "not_relevant" | "watch" | "draft_graph" | "priority_review";
  failed_gates: string[];
  matched_pillars: string[];
  candidate_parents: string[];
  contribution_types: string[];
  overlaps_with: string[];
  fills_gaps: string[];
  limitations: string[];
  reasoning_summary: string;
  confidence: number;
  provider_name: string | null;
  model_name: string | null;
  prompt_version: string | null;
  created_at: string;
};

export type DocumentGraphEvidence = {
  id: string;
  location: Record<string, unknown>;
  excerpt: string | null;
  extraction_method: string | null;
};

export type DocumentGraphNode = {
  id: string;
  node_type: string;
  label: string;
  summary: string;
  parent_node_id: string | null;
  confidence: number;
  evidence_status: string;
  evidence: DocumentGraphEvidence[];
  ai_research?: {
    research_summary: string;
    comparison_status: "consistent" | "different" | "insufficient";
    difference_summary: string;
    confidence: number;
    provider_name: string;
    model_name: string;
    prompt_version: string;
    researched_at: string;
  } | null;
};

export type DocumentGraphEdge = {
  id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  confidence: number;
  evidence_status: string;
  evidence: DocumentGraphEvidence[];
};

export type DocumentGraph = {
  workspace_id: string;
  nodes: DocumentGraphNode[];
  edges: DocumentGraphEdge[];
  meta: Record<string, unknown>;
};

export type DocumentGraphResearchResult = {
  graph: DocumentGraph;
  change_set: GraphChangeSet | null;
};

export type OntologyCandidate = {
  node_id: string;
  canonical_label: string;
  node_type: string;
  primary_parent_id: string | null;
  matched_by: "canonical_label" | "alias" | "similarity";
  score: number;
};

export type GraphMutation = {
  id: string;
  mutation_order: number;
  operation: string;
  target_kind: string;
  target_id: string | null;
  before_json: Record<string, unknown>;
  proposed_json: Record<string, unknown>;
  validation_status: string;
  validation_messages: Array<{ level: string; code: string; message: string }>;
  review_decision: string;
  reviewed_by: string | null;
  created_at: string;
  updated_at: string;
};

export type GraphChangeSet = {
  id: string;
  origin_type: string;
  origin_id: string | null;
  title: string;
  summary: string;
  lifecycle_status: string;
  validation_summary: Record<string, number>;
  created_by: string;
  approved_by: string | null;
  applied_at: string | null;
  mutations: GraphMutation[];
  created_at: string;
  updated_at: string;
};

export type GraphChangeSetList = { items: GraphChangeSet[]; total: number };

export type ChatScopeType = "graph" | "pillar" | "node" | "document" | "change_set" | "gap";

export type ChatSession = {
  id: string;
  title: string;
  scope_type: ChatScopeType;
  scope_id: string | null;
  provider_name: string;
  credential_source?: "system" | "personal";
  model_name: string;
  conversation_summary: string;
  status: string;
  prompt_version: string;
  source_type: "local" | "chatgpt_shared";
  source_url: string | null;
  source_snapshot_hash: string | null;
  source_imported_at: string | null;
  imported_message_count: number;
  message_count: number;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  provider_response_id: string | null;
  provider_request_id: string | null;
  tool_calls: Array<{ call_id: string; name: string; arguments: Record<string, unknown> }>;
  tool_results: Array<Record<string, unknown>>;
  linked_change_set_id: string | null;
  usage: Record<string, number>;
  latency_ms: number | null;
  error_code: string | null;
  origin_type: "local" | "chatgpt_shared";
  media: Array<{ type: "image"; url: string; alt: string }>;
  created_at: string;
};

export type ChatSessionList = { items: ChatSession[]; total: number };

export type ChatTurn = {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  change_set_id: string | null;
};
