import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchEventDetail, sendEventChat, acknowledgeEvent, resolveEvent } from '../api/client'
import type { EventDetail, ChatMessage, ChatResponse } from '../types/incident'

const SEV: Record<string, string> = {
  critical: 'bg-red-500 text-white', high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-400 text-black', low: 'bg-blue-500 text-white', info: 'bg-gray-400 text-white',
}
const ST: Record<string, string> = {
  open: 'text-red-600 border-red-300 bg-red-50', acknowledged: 'text-yellow-600 border-yellow-300 bg-yellow-50',
  resolved: 'text-green-600 border-green-300 bg-green-50', closed: 'text-gray-500 border-gray-300 bg-gray-50',
  reopened: 'text-orange-500 border-orange-300 bg-orange-50',
}

function fmtDate(iso: string | null | undefined) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function EventDetailPage() {
  const { eventId } = useParams<{ eventId: string }>()
  const id = Number(eventId)
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery<EventDetail>({
    queryKey: ['event-detail', id],
    queryFn: () => fetchEventDetail(id),
    enabled: !!id,
  })

  const ackMut = useMutation({
    mutationFn: () => acknowledgeEvent(id, 'operator'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['event-detail', id] }),
  })
  const resolveMut = useMutation({
    mutationFn: (note: string) => resolveEvent(id, 'operator', note),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['event-detail', id] }),
  })

  const [chatOpen, setChatOpen] = useState(true)
  const [chatInput, setChatInput] = useState('')
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; evidence?: ChatResponse['evidence'] }>>([])
  const [chatLoading, setChatLoading] = useState(false)

  async function handleSendChat() {
    const q = chatInput.trim()
    if (!q || chatLoading) return
    setChatInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setChatLoading(true)

    const history: ChatMessage[] = messages.map(m => ({ role: m.role, content: m.content }))

    try {
      const res = await sendEventChat(id, q, history)
      setMessages(prev => [...prev, { role: 'assistant', content: res.answer, evidence: res.evidence }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '오류가 발생했습니다. 다시 시도해주세요.' }])
    } finally {
      setChatLoading(false)
    }
  }

  if (isLoading) return <div className="p-8 text-gray-500">로딩 중...</div>
  if (error || !data) return <div className="p-8 text-red-600">이벤트를 불러올 수 없습니다.</div>

  const ev = data

  return (
    <div className="space-y-5 max-w-5xl">
      <section className="bg-white rounded-lg border p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{ev.event_name}</h2>
            <div className="flex items-center gap-2 mt-2 text-sm">
              <span className={`px-2 py-0.5 rounded text-xs ${SEV[ev.severity] ?? SEV.info}`}>{ev.severity}</span>
              <span className={`px-2 py-0.5 rounded border text-xs ${ST[ev.current_status] ?? ''}`}>{ev.current_status}</span>
              <span className="text-gray-500">|</span>
              <span className="text-gray-600">{ev.host ?? '-'}</span>
              {ev.service && <><span className="text-gray-400">/</span><span className="text-gray-600">{ev.service}</span></>}
            </div>
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              <span>소스: {ev.source_system}</span>
              <span>발생: {fmtDate(ev.first_seen_at)}</span>
              <span>최종: {fmtDate(ev.last_seen_at)}</span>
              <span>횟수: {ev.occurrence_count}</span>
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            {ev.current_status === 'open' && (
              <button className="px-3 py-1.5 text-sm bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:opacity-50" disabled={ackMut.isPending} onClick={() => ackMut.mutate()}>
                {ackMut.isPending ? '처리중...' : '확인'}
              </button>
            )}
            {ev.current_status !== 'resolved' && ev.current_status !== 'closed' && (
              <button className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50" disabled={resolveMut.isPending} onClick={() => resolveMut.mutate('Resolved via UI')}>
                {resolveMut.isPending ? '처리중...' : '해결'}
              </button>
            )}
          </div>
        </div>
      </section>

      {ev.assessment && (
        <section className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">분석 결과</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded p-3">
              <div className="text-xs text-gray-500">위험도 점수</div>
              <div className="text-2xl font-bold mt-1">{ev.assessment.risk_score ?? '-'}</div>
            </div>
            <div className="bg-gray-50 rounded p-3">
              <div className="text-xs text-gray-500">반복 점수</div>
              <div className="text-2xl font-bold mt-1">{ev.assessment.recurrence_score ?? '-'}</div>
            </div>
            <div className="col-span-2 bg-gray-50 rounded p-3">
              <div className="text-xs text-gray-500">패턴 요약</div>
              <div className="text-sm mt-1">{ev.assessment.pattern_summary ?? '분석 결과 없음'}</div>
            </div>
          </div>
          {ev.assessment.probable_cause && (
            <div className="mt-3 text-sm text-gray-700">
              <span className="font-medium">추정 원인: </span>{ev.assessment.probable_cause}
            </div>
          )}
        </section>
      )}

      {ev.limitation_flags.length > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded text-sm text-yellow-800">
          일부 관련 문서가 보호 상태여서 제한된 정보만 활용 가능합니다.
          <ul className="mt-1 list-disc list-inside text-xs">
            {ev.limitation_flags.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <section className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">상태 이력</h3>
          {ev.state_history.length === 0 ? (
            <div className="text-sm text-gray-400">이력 없음</div>
          ) : (
            <div className="space-y-3">
              {ev.state_history.map(sh => (
                <div key={sh.id} className="flex gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                  <div>
                    <div className="text-gray-800">
                      {sh.previous_state && <span className="text-gray-400">{sh.previous_state} → </span>}
                      <span className="font-medium">{sh.new_state}</span>
                    </div>
                    <div className="text-xs text-gray-500">{fmtDate(sh.changed_at)} {sh.changed_by && `by ${sh.changed_by}`}</div>
                    {sh.description && <div className="text-xs text-gray-500 mt-0.5">{sh.description}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">조치 기록</h3>
          {ev.handling_records.length === 0 ? (
            <div className="text-sm text-gray-400">기록 없음</div>
          ) : (
            <div className="space-y-3">
              {ev.handling_records.map(hr => (
                <div key={hr.id} className="border rounded p-3 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium">[{hr.action_type}] {hr.action_summary}</span>
                    <span className="text-xs text-gray-400">{hr.actor}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{fmtDate(hr.executed_at)}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <section className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">관련 문서</h3>
          {ev.related_documents.length === 0 ? (
            <div className="text-sm text-gray-400">관련 문서 없음</div>
          ) : (
            <div className="space-y-2">
              {ev.related_documents.map(doc => (
                <div key={doc.id} className="border rounded p-3 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">{doc.title}</div>
                    <div className="text-xs text-gray-500">{doc.document_type ?? '문서'}</div>
                  </div>
                  <div className="flex gap-1">
                    {doc.content_available && <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">내용 가용</span>}
                    {doc.refined_available && <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">정제본</span>}
                    {doc.limitation && <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded">보호</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">관련 장애 사례</h3>
          {ev.related_incidents.length === 0 ? (
            <div className="text-sm text-gray-400">관련 사례 없음</div>
          ) : (
            <div className="space-y-2">
              {ev.related_incidents.map(inc => (
                <div key={inc.id} className="border rounded p-3 text-sm">
                  <div className="font-medium">{inc.title}</div>
                  {inc.resolution_summary && <div className="text-xs text-gray-500 mt-1">{inc.resolution_summary}</div>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {ev.recommended_actions.length > 0 && (
        <section className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">권장 조치</h3>
          <ul className="space-y-1">
            {ev.recommended_actions.map((action, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
                <span className="w-5 h-5 rounded border border-gray-300 flex items-center justify-center text-xs text-gray-400">{i + 1}</span>
                {action}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="bg-white rounded-lg border">
        <button className="w-full px-5 py-3 flex items-center justify-between font-semibold text-gray-700 hover:bg-gray-50" onClick={() => setChatOpen(!chatOpen)}>
          <span>이벤트 문맥 채팅</span>
          <span className="text-sm text-gray-400">{chatOpen ? '접기' : '펼치기'}</span>
        </button>
        {chatOpen && (
          <div className="border-t p-4">
            <div className="h-72 overflow-y-auto space-y-3 mb-3">
              {messages.length === 0 && (
                <div className="text-center text-sm text-gray-400 py-8">현재 이벤트에 대해 질문하세요.</div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                    {msg.evidence && msg.evidence.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
                        {msg.evidence.map((e, j) => (
                          <div key={j} className="text-xs text-gray-500">
                            [{e.source_type}] {e.title}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-500">응답 생성 중...</div>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <input
                className="flex-1 border rounded px-3 py-2 text-sm"
                placeholder="이 이벤트에 대해 질문하세요..."
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendChat() } }}
                disabled={chatLoading}
              />
              <button className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50" onClick={handleSendChat} disabled={chatLoading || !chatInput.trim()}>
                전송
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
