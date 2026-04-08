export type EventSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type EventStatus = 'open' | 'acknowledged' | 'resolved' | 'closed' | 'reopened'

export interface SeverityCount {
  severity: string
  count: number
}

export interface StatusCount {
  status: string
  count: number
}

export interface TopRiskEvent {
  id: number
  event_name: string
  severity: string
  host: string | null
  occurrence_count: number
  risk_score: number | null
  current_status: string
  first_seen_at: string
}

export interface RecentActivity {
  id: number
  event_name: string
  action: string
  actor: string | null
  timestamp: string
}

export interface DashboardData {
  total_events: number
  open_events: number
  critical_events: number
  resolved_today: number
  severity_distribution: SeverityCount[]
  status_distribution: StatusCount[]
  top_risk_events: TopRiskEvent[]
  recent_activities: RecentActivity[]
  recurring_event_count: number
}

export interface EventListItem {
  id: number
  event_name: string
  severity: string
  host: string | null
  service: string | null
  current_status: string
  first_seen_at: string
  last_seen_at: string | null
  occurrence_count: number
  source_system: string
  has_assessment: boolean
  has_related_docs: boolean
  risk_score: number | null
  recurrence_score: number | null
}

export interface EventListResponse {
  events: EventListItem[]
  total: number
  page: number
  page_size: number
}

export interface StateHistoryItem {
  id: number
  previous_state: string | null
  new_state: string
  changed_by: string | null
  source: string | null
  description: string | null
  changed_at: string
}

export interface HandlingRecordItem {
  id: number
  action_type: string
  action_summary: string
  action_details: string | null
  actor: string
  executed_at: string
  related_ticket: string | null
  result_status: string | null
}

export interface AssessmentDetail {
  id: number
  recurrence_score: number | null
  risk_score: number | null
  pattern_summary: string | null
  probable_cause: string | null
  transfer_to_incident: boolean
  analyzed_at: string | null
  analyzer_type: string | null
}

export interface RelatedDocumentBrief {
  id: number
  title: string
  document_type: string | null
  protection_type: string
  content_available: boolean
  refined_available: boolean
  limitation: string | null
}

export interface RelatedIncidentBrief {
  id: number
  title: string
  severity: string | null
  occurred_at: string | null
  resolution_summary: string | null
}

export interface MetricLogEvidenceItem {
  id: number
  evidence_type: string
  source: string
  summary: string
  collected_at: string
}

export interface EventDetail {
  id: number
  event_name: string
  severity: string
  host: string | null
  service: string | null
  current_status: string
  source_system: string
  source_event_id: string
  first_seen_at: string
  last_seen_at: string | null
  occurrence_count: number
  raw_payload_reference: string | null
  created_at: string
  state_history: StateHistoryItem[]
  handling_records: HandlingRecordItem[]
  assessment: AssessmentDetail | null
  metric_log_evidence: MetricLogEvidenceItem[]
  related_documents: RelatedDocumentBrief[]
  related_incidents: RelatedIncidentBrief[]
  recommended_actions: string[]
  limitation_flags: string[]
}

export interface AnalysisReport {
  occurrence_id: number
  event_name: string
  generated_at: string
  analyzer_type: string
  summary: string
  probable_causes: string[]
  risk_level: string
  risk_score: number
  recurrence_analysis: string
  recurrence_score: number
  recommended_actions: string[]
  related_patterns: string[]
  evidence_used: Record<string, unknown>[]
  limitation_flags: string[]
}

export interface ChatEvidence {
  source_id: string
  source_type: string
  title: string
  content_preview: string | null
  relevance_score: number
}

export interface ChatResponse {
  answer: string
  evidence: ChatEvidence[]
  limitation_notice: string | null
  limitation_flags: string[]
  requires_manual_confirmation: boolean
  conversation_id: string | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
