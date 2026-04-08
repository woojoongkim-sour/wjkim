import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { fetchEvents } from '../api/client'
import type { EventListResponse, EventListItem } from '../types/incident'

const SEV_COLORS: Record<string, string> = {
  critical: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-400 text-black',
  low: 'bg-blue-500 text-white',
  info: 'bg-gray-400 text-white',
}

const STATUS_COLORS: Record<string, string> = {
  open: 'text-red-600 border-red-300 bg-red-50',
  acknowledged: 'text-yellow-600 border-yellow-300 bg-yellow-50',
  resolved: 'text-green-600 border-green-300 bg-green-50',
  closed: 'text-gray-500 border-gray-300 bg-gray-50',
  reopened: 'text-orange-500 border-orange-300 bg-orange-50',
}

function fmtDate(iso: string | null) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function EventListPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()

  const severity = params.get('severity') || ''
  const status = params.get('status') || ''
  const host = params.get('host') || ''
  const search = params.get('search') || ''
  const page = Number(params.get('page') || '1')

  const queryParams = {
    customer_id: 1,
    page,
    page_size: 30,
    ...(severity && { severity }),
    ...(status && { current_status: status }),
    ...(host && { host }),
    ...(search && { search }),
  }

  const { data, isLoading, error } = useQuery<EventListResponse>({
    queryKey: ['events', queryParams],
    queryFn: () => fetchEvents(queryParams),
  })

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.set('page', '1')
    setParams(next)
  }

  function setPage(p: number) {
    const next = new URLSearchParams(params)
    next.set('page', String(p))
    setParams(next)
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-4 flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">심각도</label>
          <select className="border rounded px-2 py-1.5 text-sm" value={severity} onChange={e => setFilter('severity', e.target.value)}>
            <option value="">전체</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">상태</label>
          <select className="border rounded px-2 py-1.5 text-sm" value={status} onChange={e => setFilter('status', e.target.value)}>
            <option value="">전체</option>
            <option value="open">Open</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">호스트</label>
          <input className="border rounded px-2 py-1.5 text-sm w-40" placeholder="호스트 검색" value={host} onChange={e => setFilter('host', e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">검색</label>
          <input className="border rounded px-2 py-1.5 text-sm w-48" placeholder="이벤트명 검색" value={search} onChange={e => setFilter('search', e.target.value)} />
        </div>
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        {isLoading && <div className="p-8 text-center text-gray-500">로딩 중...</div>}
        {error && <div className="p-8 text-center text-red-600">데이터를 불러올 수 없습니다.</div>}
        {data && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-2 text-center">심각도</th>
                    <th className="px-4 py-2 text-left">이벤트명</th>
                    <th className="px-4 py-2 text-left">호스트</th>
                    <th className="px-4 py-2 text-center">상태</th>
                    <th className="px-4 py-2 text-left">발생시각</th>
                    <th className="px-4 py-2 text-center">횟수</th>
                    <th className="px-4 py-2 text-center">분석</th>
                  </tr>
                </thead>
                <tbody>
                  {data.events.map((ev: EventListItem) => (
                    <tr
                      key={ev.id}
                      className="border-t hover:bg-blue-50 cursor-pointer"
                      onClick={() => navigate(`/events/${ev.id}`)}
                    >
                      <td className="px-4 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs ${SEV_COLORS[ev.severity] ?? SEV_COLORS.info}`}>{ev.severity}</span>
                      </td>
                      <td className="px-4 py-2 font-medium text-gray-800">{ev.event_name}</td>
                      <td className="px-4 py-2 text-gray-600">{ev.host ?? '-'}</td>
                      <td className="px-4 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded border text-xs ${STATUS_COLORS[ev.current_status] ?? ''}`}>{ev.current_status}</span>
                      </td>
                      <td className="px-4 py-2 text-gray-500">{fmtDate(ev.first_seen_at)}</td>
                      <td className="px-4 py-2 text-center font-mono">{ev.occurrence_count}</td>
                      <td className="px-4 py-2 text-center">
                        {ev.has_assessment ? <span className="text-green-600">✓</span> : <span className="text-gray-300">—</span>}
                      </td>
                    </tr>
                  ))}
                  {data.events.length === 0 && (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">이벤트 없음</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="px-4 py-3 border-t flex items-center justify-between text-sm">
              <span className="text-gray-500">총 {data.total}건</span>
              <div className="flex items-center gap-2">
                <button
                  className="px-3 py-1 border rounded disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >이전</button>
                <span className="text-gray-600">{page} / {totalPages || 1}</span>
                <button
                  className="px-3 py-1 border rounded disabled:opacity-40"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                >다음</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
