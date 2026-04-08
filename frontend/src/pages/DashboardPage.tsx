import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchDashboard } from '../api/client'
import type { DashboardData, TopRiskEvent } from '../types/incident'

const SEV_COLORS: Record<string, string> = {
  critical: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-400 text-black',
  low: 'bg-blue-500 text-white',
  info: 'bg-gray-400 text-white',
}

const STATUS_COLORS: Record<string, string> = {
  open: 'text-red-600 border-red-300',
  acknowledged: 'text-yellow-600 border-yellow-300',
  resolved: 'text-green-600 border-green-300',
  closed: 'text-gray-500 border-gray-300',
  reopened: 'text-orange-500 border-orange-300',
}

function sevBadge(sev: string) {
  return SEV_COLORS[sev] ?? SEV_COLORS.info
}
function statusBadge(st: string) {
  return STATUS_COLORS[st] ?? STATUS_COLORS.closed
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery<DashboardData>({
    queryKey: ['dashboard', 1],
    queryFn: () => fetchDashboard(1),
  })

  if (isLoading) return <div className="text-gray-500 p-8">로딩 중...</div>
  if (error) return <div className="text-red-600 p-8">데이터를 불러올 수 없습니다.</div>
  if (!data) return null

  const stats = [
    { label: '전체 이벤트', value: data.total_events, color: 'text-gray-800' },
    { label: '미처리 이벤트', value: data.open_events, color: 'text-red-600' },
    { label: '긴급 이벤트', value: data.critical_events, color: 'text-red-700' },
    { label: '오늘 해결', value: data.resolved_today, color: 'text-green-600' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => (
          <div key={s.label} className="bg-white rounded-lg border p-4">
            <div className="text-sm text-gray-500">{s.label}</div>
            <div className={`text-3xl font-bold mt-1 ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white rounded-lg border">
          <div className="px-4 py-3 border-b font-semibold text-gray-700">위험도 상위 이벤트</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">이벤트명</th>
                  <th className="px-4 py-2 text-left">호스트</th>
                  <th className="px-4 py-2 text-center">심각도</th>
                  <th className="px-4 py-2 text-center">횟수</th>
                  <th className="px-4 py-2 text-center">위험도</th>
                  <th className="px-4 py-2 text-center">상태</th>
                </tr>
              </thead>
              <tbody>
                {data.top_risk_events.map((ev: TopRiskEvent) => (
                  <tr key={ev.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <Link to={`/events/${ev.id}`} className="text-blue-600 hover:underline">{ev.event_name}</Link>
                    </td>
                    <td className="px-4 py-2 text-gray-600">{ev.host ?? '-'}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${sevBadge(ev.severity)}`}>{ev.severity}</span>
                    </td>
                    <td className="px-4 py-2 text-center font-mono">{ev.occurrence_count}</td>
                    <td className="px-4 py-2 text-center font-mono">{ev.risk_score ?? '-'}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded border text-xs ${statusBadge(ev.current_status)}`}>{ev.current_status}</span>
                    </td>
                  </tr>
                ))}
                {data.top_risk_events.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">데이터 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-lg border">
          <div className="px-4 py-3 border-b font-semibold text-gray-700">심각도 분포</div>
          <div className="p-4 space-y-2">
            {data.severity_distribution.map(s => (
              <div key={s.severity} className="flex items-center gap-2 text-sm">
                <span className={`w-3 h-3 rounded-full ${sevBadge(s.severity).split(' ')[0]}`} />
                <span className="flex-1">{s.severity}</span>
                <span className="font-mono font-semibold">{s.count}</span>
              </div>
            ))}
          </div>
          <div className="px-4 py-3 border-t">
            <div className="text-xs text-gray-500">반복 이벤트: <span className="font-semibold">{data.recurring_event_count}</span>건</div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border">
        <div className="px-4 py-3 border-b font-semibold text-gray-700">최근 활동</div>
        <ul className="divide-y">
          {data.recent_activities.map(a => (
            <li key={a.id} className="px-4 py-3 flex justify-between text-sm">
              <div>
                <span className="font-medium text-gray-800">{a.event_name}</span>
                <span className="text-gray-500 ml-2">— {a.action}</span>
              </div>
              <div className="text-gray-400 text-xs shrink-0 ml-4">
                {a.actor && <span className="mr-2">{a.actor}</span>}
                {fmtDate(a.timestamp)}
              </div>
            </li>
          ))}
          {data.recent_activities.length === 0 && (
            <li className="px-4 py-6 text-center text-gray-400 text-sm">최근 활동 없음</li>
          )}
        </ul>
      </div>
    </div>
  )
}
