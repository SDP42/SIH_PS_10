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
  confidence: number;
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
