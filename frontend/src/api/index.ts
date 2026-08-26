import apiClient from './client';

export interface Stats {
  namaste_concepts: number;
  icd11_concepts: number;
  total_mappings: number;
  validated_mappings: number;
  related_mappings: number;
  mapped_namaste_codes: number;
  mapped_icd11_codes: number;
  terminologies: Terminology[];
}

export interface Terminology {
  id: string;
  name: string;
  full_name: string;
  version: string;
  status: string;
  concept_count: number;
  source: string;
  url?: string;
  description?: string;
}

export interface ConceptResult {
  code: string;
  display: string;
  name_english?: string;
  definition?: string;
  system: string;
  system_id: string;
  native_script?: string | null;
  native_script_language?: string | null;
  tradition?: string;
}

export interface ConceptsResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  system: string;
  results: ConceptResult[];
}

export interface SearchResponse {
  query: string;
  total: number;
  namaste_count: number;
  icd11_count: number;
  results: ConceptResult[];
}

export interface Mapping {
  id: number;
  source_system: string;
  source_code: string;
  source_display: string;
  source_english?: string;
  source_definition?: string;
  target_system: string;
  target_code: string;
  target_display: string;
  equivalence: string;
  // Real backend-computed embedding similarity + lexical overlap (see
  // app/ai_mapping.py:score_pair) — null only when the AI embeddings
  // haven't been built, never a fake fallback number.
  confidence: number | null;
}

export interface MappingDetail extends Mapping {
  source_devanagari?: string;
  status: string;
  version: string;
}

export interface MappingsResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: Mapping[];
}

export interface ConceptMapBundle {
  resourceType: string;
  type: string;
  total: number;
  available_codes: string[];
  message: string;
}

export interface FhirConceptMap {
  resourceType: string;
  id: string;
  url: string;
  version: string;
  name: string;
  title: string;
  status: string;
  date: string;
  publisher: string;
  description: string;
  group: FhirGroup[];
}

export interface FhirGroup {
  source: string;
  target: string;
  element: FhirElement[];
}

export interface FhirElement {
  code: string;
  display?: string;
  target: FhirTarget[];
}

export interface FhirTarget {
  code: string;
  display?: string;
  equivalence?: string;
  relationship?: string;
}

// ---- API calls ----

export const getStats = () =>
  apiClient.get<Stats>('/api/stats').then((r) => r.data);

export const getTerminologies = () =>
  apiClient.get<Terminology[]>('/api/terminologies').then((r) => r.data);

export const getConcepts = (params: {
  system?: string;
  q?: string;
  page?: number;
  page_size?: number;
}) => apiClient.get<ConceptsResponse>('/api/concepts', { params }).then((r) => r.data);

export const searchConcepts = (params: {
  q: string;
  system?: string;
  page?: number;
  page_size?: number;
}) => apiClient.get<SearchResponse>('/api/search', { params }).then((r) => r.data);

export const getMappings = (params: {
  source_code?: string;
  target_code?: string;
  equivalence?: string;
  q?: string;
  page?: number;
  page_size?: number;
}) => apiClient.get<MappingsResponse>('/api/mappings', { params }).then((r) => r.data);

export const getMappingById = (id: number) =>
  apiClient.get<MappingDetail>(`/api/mappings/${id}`).then((r) => r.data);

export const getConcept = (system: string, code: string) =>
  apiClient.get(`/api/concept/${system}/${encodeURIComponent(code)}`).then((r) => r.data);

export const getConceptMapList = () =>
  apiClient.get<ConceptMapBundle>('/ConceptMap').then((r) => r.data);

export const getFhirConceptMap = (code: string) =>
  apiClient.get<FhirConceptMap>(`/ConceptMap/${encodeURIComponent(code)}`).then((r) => r.data);

export const getRootInfo = () =>
  apiClient.get('/').then((r) => r.data);

// ---- AI Mapping Engine (ambiguity-aware) ----

export type AiDecision = 'AUTO_SUGGEST' | 'NEEDS_CONTEXT' | 'EXPERT_REVIEW' | 'NO_VALIDATED_EQUIVALENT';

export interface AiCandidate {
  icd11_code: string;
  icd11_title: string;
  similarity: number;
  semantic_score: number;
  lexical_score: number;
  shared_terms: string[];
  rank: number;
}

export interface CuratedMapping {
  target_code: string;
  equivalence: string;
  target_title?: string;
}

export interface AiSuggestion {
  namaste_code: string;
  source_system: string;
  decision: AiDecision;
  margin: number | null;
  candidates: AiCandidate[];
  rationale: string;
  has_curated_mapping: boolean;
  curated_mappings: CuratedMapping[];
  disclaimer: string;
}

export interface UnmappedConcept {
  system: string;
  code: string;
  display_text: string;
}

export interface UnmappedResponse {
  total_unmapped: number;
  page: number;
  page_size: number;
  concepts: UnmappedConcept[];
}

export const getAiSuggestion = (code: string, params?: { source_system?: string; top_k?: number }) =>
  apiClient.get<AiSuggestion>(`/api/ai/suggest/${encodeURIComponent(code)}`, { params }).then((r) => r.data);

export const getUnmapped = (params: { page?: number; page_size?: number; source_system?: string }) =>
  apiClient.get<UnmappedResponse>('/api/ai/unmapped', { params }).then((r) => r.data);

export interface BatchSuggestResponse {
  requested: number;
  results: (AiSuggestion | { namaste_code: string; error: string })[];
}

export const batchSuggest = (body: { codes?: string[]; all_unmapped?: boolean; limit?: number; source_system?: string }) =>
  apiClient.post<BatchSuggestResponse>('/api/ai/batch_suggest', body).then((r) => r.data);

// ---- Governance / Review Queue ----

export interface ReviewQueueItem {
  id: number;
  source_system: string;
  source_code: string;
  ai_suggested_code: string | null;
  ai_suggested_title: string | null;
  confidence: number | null;
  decision: AiDecision;
  rationale: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'needs_info';
  reviewer_note: string | null;
  reviewed_at: string | null;
  created_at: string;
  flag_type: 'ai_suggestion' | 'legacy_reclassification';
  target_system: string | null;
}

export interface ReviewQueueResponse {
  total: number;
  page: number;
  page_size: number;
  items: ReviewQueueItem[];
}

export const getReviewQueue = (params?: { status?: string; page?: number; page_size?: number }) =>
  apiClient.get<ReviewQueueResponse>('/api/governance/queue', { params }).then((r) => r.data);

export const decideReviewItem = (id: number, body: { status: string; note?: string }) =>
  apiClient.post(`/api/governance/${id}/decide`, body).then((r) => r.data);

// ---- FHIR $translate ----

export interface FhirParameters {
  resourceType: string;
  parameter: Array<Record<string, unknown>>;
}

export const translateConcept = (params: { system: string; code: string; target_system?: string }) =>
  apiClient.get<FhirParameters>('/ConceptMap/$translate', { params }).then((r) => r.data);

export const uploadBundle = (bundle: Record<string, unknown>) =>
  apiClient.post<Record<string, unknown>>('/Bundle', bundle).then((r) => r.data);

export const buildProblemListEntry = (body: { namaste_code: string; source_system?: string; patient_reference?: string }) =>
  apiClient.post<Record<string, unknown>>('/api/problem-list/build', body).then((r) => r.data);

// ---- ABHA Demo Mode auth ----

export interface DemoAuthSession {
  access_token: string;
  token_type: string;
  expires_in: number;
  identity: { name: string; role: string };
  mode: string;
  disclaimer: string;
}

export const demoLogin = (name: string, role: string) =>
  apiClient.post<DemoAuthSession>('/api/auth/demo-login', { name, role }).then((r) => r.data);

export const whoami = () =>
  apiClient.get<{ name: string; role: string; mode: string }>('/api/auth/whoami').then((r) => r.data);

// ---- Audit trail (real) ----

export interface AuditEvent {
  id: number;
  action: string;
  actor: string;
  target: string | null;
  details: string | null;
  created_at: string;
}

export const getRecentAudit = (limit = 10) =>
  apiClient.get<{ events: AuditEvent[] }>('/api/audit/recent', { params: { limit } }).then((r) => r.data);

// ---- Dual TM2 + Biomedicine AI candidates ----

export interface DualAiSuggestion {
  namaste_code: string;
  source_system: string;
  tm2: AiSuggestion;
  biomedicine: AiSuggestion;
  disclaimer: string;
}

export const getDualAiSuggestion = (code: string) =>
  apiClient.get<DualAiSuggestion>(`/api/ai/suggest/${encodeURIComponent(code)}/dual`).then((r) => r.data);

// ---- WHO ICD-11 API synchronisation ----

export type WhoProvenance = 'WHO_LIVE' | 'WHO_CACHE' | 'WHO_RELEASE_FILE' | 'LOCAL_SNAPSHOT';

export interface WhoSyncRun {
  id: number;
  run_at: string;
  release_id: string;
  actor: string | null;
  mode: string;
  source: 'release_file' | 'api';
  codes_checked: number;
  confirmed: number;
  drifted: number;
  missing: number;
  errored: number;
  duration_seconds: number | null;
  detail: string | null;
}

export interface WhoStatus {
  credentials_configured: boolean;
  snapshot_release: string;
  snapshot_label: string;
  token_endpoint: string;
  api_root: string;
  release_file_base: string;
  registration_url: string;
  last_sync: WhoSyncRun | null;
  last_release_sync: WhoSyncRun | null;
  last_api_sync: WhoSyncRun | null;
  release_sync_coverage_pct: number;
  codes_cached_from_who: number;
  mapping_target_codes: number;
  coverage_pct: number;
  open_drift_items: number;
  mode: 'LIVE_VERIFIED' | 'LIVE_CAPABLE' | 'SNAPSHOT_ONLY';
  disclaimer: string;
}

export interface WhoReleases {
  provenance: WhoProvenance;
  degraded_reason?: string | null;
  snapshot_release: string;
  releases: string[];
  latest: string | null;
  snapshot_is_latest?: boolean | null;
  releases_behind?: number | null;
}

export interface WhoCodeLookup {
  code: string;
  release_id: string;
  provenance: WhoProvenance;
  degraded_reason: string | null;
  who: {
    entity_id: string | null;
    title: string | null;
    definition: string | null;
    class_kind: string | null;
    browser_url: string | null;
  } | null;
  local: { code: string; title: string; class_kind: string; chapter: string } | null;
  comparison: { status: string; message: string; local_title?: string; who_title?: string };
  checked_at: string;
  disclaimer: string;
}

export interface WhoDriftItem {
  code: string;
  release_id: string;
  drift_type: string;
  local_title: string | null;
  who_title: string | null;
  detected_at: string;
}

export interface WhoSyncResult extends Omit<WhoSyncRun, 'id' | 'actor'> {
  results: Array<{ code: string; status: string; local_title?: string | null; who_title?: string | null; browser_url?: string | null }>;
  release_version_label?: string | null;
  release_code_count?: number | null;
  disclaimer: string;
}

export const getWhoStatus = () =>
  apiClient.get<WhoStatus>('/api/who/status').then((r) => r.data);

export const getWhoReleases = () =>
  apiClient.get<WhoReleases>('/api/who/releases').then((r) => r.data);

export const lookupWhoCode = (code: string, opts: { release?: string; force?: boolean } = {}) =>
  apiClient.get<WhoCodeLookup>(`/api/who/code/${encodeURIComponent(code)}`, { params: opts }).then((r) => r.data);

export const getWhoDrift = (limit = 100) =>
  apiClient.get<{ items: WhoDriftItem[] }>('/api/who/drift', { params: { limit } }).then((r) => r.data);

export const getWhoHistory = (limit = 20) =>
  apiClient.get<{ runs: WhoSyncRun[] }>('/api/who/history', { params: { limit } }).then((r) => r.data);

/** Default sync — diffs every mapping target against WHO's public release file. No credentials needed. */
export const runWhoReleaseSync = (body: { release?: string } = {}) =>
  apiClient.post<WhoSyncResult>('/api/who/sync', body).then((r) => r.data);

/** ICD-API sweep — needs ICD_API_CLIENT_ID/SECRET server-side; adds definitions + browser links. */
export const runWhoApiSync = (body: { limit?: number; release?: string } = {}) =>
  apiClient.post<WhoSyncResult>('/api/who/sync/api', body).then((r) => r.data);

// ---- Governance & interoperability analytics ----

export interface TraditionCoverage {
  system: string;
  label: string;
  corpus_size: number;
  unmapped: number | null;
  mapped: number | null;
  coverage_pct: number | null;
}

export interface MappingRegistryStats {
  total_mappings: number;
  equivalent: number;
  related: number;
  curated_rule_based: number;
  ai_reviewed: number;
  target_tm2: number;
  target_biomedicine: number;
}

export interface ReviewQueueStats {
  pending: number;
  approved: number;
  rejected: number;
  needs_info: number;
  by_decision_tier: Record<string, number>;
  ai_suggestions: number;
  legacy_reclassifications: number;
  avg_review_turnaround_hours: number | null;
}

export interface AnalyticsOverview {
  generated_at: string;
  traditions: TraditionCoverage[];
  mapping_registry: MappingRegistryStats;
  review_queue: ReviewQueueStats;
  who_sync: {
    mode: string;
    snapshot_release: string;
    open_drift_items: number;
    release_sync_coverage_pct: number;
    last_release_sync: { run_at: string; mode: string; codes_checked: number } | null;
  };
  audit_activity: Array<{ day: string; n: number }>;
  audit_action_breakdown: Array<{ action: string; n: number }>;
  data_honesty_note: string;
}

export const getAnalyticsOverview = () =>
  apiClient.get<AnalyticsOverview>('/api/analytics/overview').then((r) => r.data);

// ---- Human clinical-text -> terminology assistant (Phase 1) ----

export interface ExtractedSymptom {
  surface_form: string;
  symptom: string;
  negated: boolean;
  duration: string | null;
  body_site: string | null;
  laterality: string | null;
}

export interface SymptomCandidate extends ExtractedSymptom {
  candidates: ConceptResult[];
  searched: boolean;
  no_candidates_found?: boolean;
}

export interface ClinicalTextCandidatesResponse {
  input_text: string;
  detected_symptoms: SymptomCandidate[];
  negated_symptoms: SymptomCandidate[];
  diagnosis_inferred: false;
  requires_clinician_confirmation: true;
  safety_note: string;
}

export const getClinicalTextCandidates = (text: string) =>
  apiClient.post<ClinicalTextCandidatesResponse>('/api/v1/clinical-text/candidates', { text }).then((r) => r.data);

// ---- API Key / Developer Platform ----

export interface ApiClient {
  id: number;
  name: string;
  organization: string | null;
  status: string;
}

export interface ApiKeyMeta {
  id: number;
  client_id: number;
  key_type: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  label: string | null;
  created_by?: string;
  created_at?: string;
  expires_at: string | null;
  revoked_at?: string | null;
  rotated_from_id?: number | null;
  last_used_at?: string | null;
}

export interface ApiKeyCreated extends ApiKeyMeta {
  secret: string;
  warning: string;
}

export interface ApiUsageSummary {
  key_id: number;
  window_hours: number;
  total_requests: number;
  by_path: Array<{ path: string; n: number }>;
  recent: Array<{ method: string; path: string; status_code: number | null; occurred_at: string }>;
}

export const createApiClient = (name: string, organization?: string) =>
  apiClient.post<ApiClient>('/api/v1/api-keys/clients', { name, organization }).then((r) => r.data);

export const createApiKey = (body: { client_id: number; key_type: string; label?: string; expires_in_days?: number }) =>
  apiClient.post<ApiKeyCreated>('/api/v1/api-keys', body).then((r) => r.data);

export const listApiKeys = (client_id?: number) =>
  apiClient.get<{ keys: ApiKeyMeta[] }>('/api/v1/api-keys', { params: client_id ? { client_id } : {} }).then((r) => r.data);

export const rotateApiKey = (id: number) =>
  apiClient.post<ApiKeyCreated>(`/api/v1/api-keys/${id}/rotate`).then((r) => r.data);

export const revokeApiKey = (id: number) =>
  apiClient.post<ApiKeyMeta>(`/api/v1/api-keys/${id}/revoke`).then((r) => r.data);

export const getApiKeyUsage = (id: number, hours = 24) =>
  apiClient.get<ApiUsageSummary>(`/api/v1/api-keys/${id}/usage`, { params: { hours } }).then((r) => r.data);

export const getApiScopes = () =>
  apiClient.get<{ all_scopes: string[]; defaults_by_key_type: Record<string, string[]>; rate_limits_by_key_type: Record<string, number> }>(
    '/api/v1/api-keys/scopes'
  ).then((r) => r.data);

export const getCapabilityStatement = () =>
  apiClient.get<Record<string, unknown>>('/api/v1/CapabilityStatement').then((r) => r.data);

// ---- Population Health Demo (SYNTHETIC data — see backend disclaimer) ----

export interface PopulationDemoPayload {
  is_synthetic: true;
  available: boolean;
  disclaimer: string;
  message?: string;
  overview?: {
    total_patients: number;
    total_encounters: number;
    date_range: { from: string | null; to: string | null };
    regions_covered: number;
  };
  by_gender?: Array<{ gender: string; n: number }>;
  by_age_band?: Array<{ age_band: string; n: number }>;
  by_region?: Array<{ region: string; patients: number; encounters: number }>;
  by_month?: Array<{ month: string; n: number }>;
  by_tradition?: Array<{ tradition: string; n: number }>;
  gender_by_region?: Array<Record<string, string | number>>;
}

export const getPopulationDemo = () =>
  apiClient.get<PopulationDemoPayload>('/api/analytics/population-demo').then((r) => r.data);

// ---- Terminology What-If Simulator (Phase 3) ----

export interface SimulationResult {
  id: number;
  from_release: string;
  to_release: string;
  run_at: string;
  run_by: string;
  new_concepts: number;
  deprecated_concepts: number;
  retitled_concepts: number;
  broken_mappings: number;
  ambiguous_mappings: number;
  total_mappings_checked: number;
  from_release_concept_count: number;
  to_release_concept_count: number;
  risk_score: 'LOW' | 'MEDIUM' | 'HIGH';
  disclaimer: string;
}

export interface AffectedMapping {
  id: number;
  simulation_id: number;
  concept_map_id: number | null;
  source_system: string;
  source_code: string;
  target_code: string;
  impact_type: 'BROKEN_MAPPING' | 'AMBIGUOUS_MAPPING';
  old_title: string | null;
  new_title: string | null;
  review_queue_id: number | null;
}

export const getSimulatorReleases = () =>
  apiClient.get<{ releases: string[]; latest: string | null; snapshot_release: string }>('/api/v1/terminology/releases').then((r) => r.data);

export const runSimulation = (from_release: string, to_release: string) =>
  apiClient.post<SimulationResult>('/api/v1/terminology/simulate', { from_release, to_release }).then((r) => r.data);

export const getAffectedMappings = (simId: number) =>
  apiClient.get<{ items: AffectedMapping[] }>(`/api/v1/terminology/simulate/${simId}/affected-mappings`).then((r) => r.data);

export const escalateSimulation = (simId: number) =>
  apiClient.post<{ simulation_id: number; review_queue_ids: number[]; count: number }>(`/api/v1/terminology/simulate/${simId}/escalate`).then((r) => r.data);

export const getSimulationHistory = () =>
  apiClient.get<{ simulations: SimulationResult[] }>('/api/v1/terminology/simulations').then((r) => r.data);

// ---- Tamper-evident audit chain (Phase 3B) ----

export interface AuditVerifyResult {
  valid: boolean;
  broken_at_id: number | null;
  reason: string | null;
  rows_checked: number;
  total_rows: number;
}

export const verifyAuditChain = () =>
  apiClient.get<AuditVerifyResult>('/api/audit/verify').then((r) => r.data);
