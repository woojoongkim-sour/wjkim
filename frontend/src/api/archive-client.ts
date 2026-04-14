import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

export async function login(username: string, password: string) {
  const { data } = await api.post('/auth/login', { username, password })
  setAuthToken(data.access_token)
  return data
}

export async function logout() {
  setAuthToken(null)
}

export async function getCurrentUser() {
  const { data } = await api.get('/auth/me')
  return data
}

export interface SearchResult {
  chunk_id: number
  document_id: number
  document_title: string
  section_title?: string
  content: string
  customer_id: number
  score: number
  dense_score?: number
  sparse_score?: number
  keyword_score?: number
  version?: number
  is_latest: boolean
  created_at?: string
}

export interface HybridSearchResponse {
  results: SearchResult[]
  total: number
  query_time_ms: number
  search_mode: string
  escalation_triggered: boolean
  dense_threshold_met: boolean
}

export interface Document {
  id: number
  customer_id: number
  title: string
  description?: string
  document_type: string
  file_name?: string
  file_size?: number
  content_hash?: string
  processing_status: string
  version?: number
  is_latest?: boolean
  created_at: string
}

export async function hybridSearch(
  query: string,
  customerId: number,
  options?: {
    includeAllVersions?: boolean
    targetDate?: string
    crossSearch?: boolean
    limit?: number
  }
): Promise<HybridSearchResponse> {
  const { data } = await api.post('/search/hybrid', {
    query,
    customer_id: customerId,
    ...options,
  })
  return data
}

export async function versionSearch(
  query: string,
  customerId: number,
  targetDate: string
): Promise<HybridSearchResponse> {
  const { data } = await api.post('/search/version', {
    query,
    customer_id: customerId,
    target_date: targetDate,
  })
  return data
}

export async function adaptiveRag(
  query: string,
  customerId: number,
  crossSearch = false
): Promise<{
  mode: string
  response: string
  tool_results: any[]
  escalation_reason?: string
}> {
  const { data } = await api.post('/search/rag', null, {
    params: { query, customer_id: customerId, cross_search: crossSearch },
  })
  return data
}

export async function uploadDocument(
  file: File,
  metadata: {
    title: string
    documentType: string
    customerId: number
    description?: string
    tags?: string
    categoryId?: number
    isVersioned?: boolean
    existingDocumentId?: number
  }
): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', metadata.title)
  formData.append('document_type', metadata.documentType)
  formData.append('customer_id', String(metadata.customerId))
  if (metadata.description) formData.append('description', metadata.description)
  if (metadata.tags) formData.append('tags', metadata.tags)
  if (metadata.categoryId) formData.append('category_id', String(metadata.categoryId))
  if (metadata.isVersioned) formData.append('is_versioned', 'true')
  if (metadata.existingDocumentId) formData.append('existing_document_id', String(metadata.existingDocumentId))

  const { data } = await api.post('/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listDocuments(
  customerId: number,
  options?: {
    documentType?: string
    processingStatus?: string
    skip?: number
    limit?: number
  }
): Promise<Document[]> {
  const { data } = await api.get('/documents', {
    params: { customer_id: customerId, ...options },
  })
  return data
}

export async function getDocumentVersions(
  documentId: number,
  customerId: number
): Promise<any[]> {
  const { data } = await api.get(`/documents/${documentId}/versions`, {
    params: { customer_id: customerId },
  })
  return data
}

export async function checkDuplicate(
  customerId: number,
  fileHash: string
): Promise<{ is_duplicate: boolean; existing_document?: any }> {
  const { data } = await api.get('/documents/check-duplicate', {
    params: { customer_id: customerId, file_hash: fileHash },
  })
  return data
}

export async function getDocumentGraphContext(
  documentId: number,
  customerId: number,
  depth = 2
): Promise<{ nodes: any[]; edges: any[] }> {
  const { data } = await api.get(`/documents/${documentId}/graph-context`, {
    params: { customer_id: customerId, depth },
  })
  return data
}
