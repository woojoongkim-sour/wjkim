import axios from 'axios'
import type {
  DashboardData,
  EventListResponse,
  EventDetail,
  AnalysisReport,
  ChatResponse,
  ChatMessage,
} from '../types/incident'

const api = axios.create({
  baseURL: '/api/v1/incident',
  headers: { 'Content-Type': 'application/json' },
})

export async function fetchDashboard(customerId: number): Promise<DashboardData> {
  const { data } = await api.get('/dashboard', { params: { customer_id: customerId } })
  return data
}

export async function fetchEvents(params: {
  customer_id: number
  page?: number
  page_size?: number
  current_status?: string
  severity?: string
  host?: string
  search?: string
  sort_by?: string
  sort_order?: string
}): Promise<EventListResponse> {
  const { data } = await api.get('/events', { params })
  return data
}

export async function fetchEventDetail(eventId: number): Promise<EventDetail> {
  const { data } = await api.get(`/events/${eventId}`)
  return data
}

export async function fetchAnalysisReport(eventId: number): Promise<AnalysisReport> {
  const { data } = await api.get(`/events/${eventId}/analysis`)
  return data
}

export async function sendEventChat(
  eventId: number,
  query: string,
  conversationHistory?: ChatMessage[],
  useSanitizedKnowledge = true,
): Promise<ChatResponse> {
  const { data } = await api.post(`/events/${eventId}/chat`, {
    query,
    conversation_history: conversationHistory,
    use_sanitized_knowledge: useSanitizedKnowledge,
  })
  return data
}

export async function acknowledgeEvent(eventId: number, actor: string) {
  const { data } = await api.post(`/events/${eventId}/acknowledge`, null, {
    params: { actor },
  })
  return data
}

export async function resolveEvent(eventId: number, actor: string, resolutionNote?: string) {
  const { data } = await api.post(`/events/${eventId}/resolve`, null, {
    params: { actor, resolution_note: resolutionNote },
  })
  return data
}
