import { useState } from 'react'
import { Outlet, NavLink } from 'react-router-dom'

export default function Layout() {
  const [customerId] = useState(1)

  return (
    <div className="min-h-screen flex bg-gray-50">
      <aside className="w-56 bg-slate-800 text-white flex flex-col shrink-0">
        <div className="px-5 py-5 text-lg font-bold tracking-tight border-b border-slate-700">
          MSP Archive
        </div>
        <nav className="flex flex-col gap-1 p-3 text-sm">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `px-3 py-2 rounded ${isActive ? 'bg-slate-600 font-medium' : 'hover:bg-slate-700'}`
            }
          >
            대시보드
          </NavLink>
          <NavLink
            to="/documents"
            className={({ isActive }) =>
              `px-3 py-2 rounded ${isActive ? 'bg-slate-600 font-medium' : 'hover:bg-slate-700'}`
            }
          >
            문서 관리
          </NavLink>
          <NavLink
            to="/events"
            className={({ isActive }) =>
              `px-3 py-2 rounded ${isActive ? 'bg-slate-600 font-medium' : 'hover:bg-slate-700'}`
            }
          >
            이벤트 목록
          </NavLink>
        </nav>
        <div className="mt-auto p-4 text-xs text-slate-400 border-t border-slate-700">
          고객사 #{customerId}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-gray-200 flex items-center px-6 shrink-0">
          <h1 className="text-lg font-semibold text-gray-800">장애분석시스템</h1>
        </header>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
