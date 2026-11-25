import React, { useMemo, useState } from 'react'
import { Search, Shield, ArrowUpDown, ChevronDown, ChevronRight } from 'lucide-react'

const FLAG_STYLES = {
  'Overloaded / Bottleneck': 'bg-rose-50 text-rose-700 border-rose-200',
  'SLA Watch': 'bg-amber-50 text-amber-700 border-amber-200',
  'Top Performer': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'On Track': 'bg-slate-100 text-slate-700 border-slate-200',
}

export default function WorkerAuditTable({ workers = [] }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [flagFilter, setFlagFilter] = useState('All')
  const [sortKey, setSortKey] = useState('remaining_count')
  const [sortDir, setSortDir] = useState('desc')
  const [expandedWorker, setExpandedWorker] = useState(null)

  const flagCounts = useMemo(() => {
    const counts = { All: workers.length }
    for (const w of workers) {
      counts[w.accountability_flag] = (counts[w.accountability_flag] || 0) + 1
    }
    return counts
  }, [workers])

  const filteredWorkers = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    const list = workers.filter((w) => {
      if (flagFilter !== 'All' && w.accountability_flag !== flagFilter) return false
      if (!q) return true
      const actionsText = (w.actions_summary || []).map((a) => a.action.toLowerCase()).join(' ')
      return (
        w.worker_id.toLowerCase().includes(q) ||
        w.primary_category.toLowerCase().includes(q) ||
        actionsText.includes(q)
      )
    })

    return [...list].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      if (typeof av === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
      }
      return sortDir === 'asc' ? av - bv : bv - av
    })
  }, [workers, searchQuery, flagFilter, sortKey, sortDir])

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-600" />
            <h2 className="text-base font-semibold text-slate-900">
              Government Worker Accountability &amp; Actions Audit
            </h2>
            <span className="text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
              Anonymized IDs Only
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Track assigned workload, completed vs. remaining backlog, SLA adherence, peer z-score, and standardized actions taken per anonymized staff ID.
          </p>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search ID (e.g. ENG-042) or action..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Flag filter chips */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {['All', 'Overloaded / Bottleneck', 'SLA Watch', 'Top Performer', 'On Track'].map((flag) => (
          <button
            key={flag}
            type="button"
            onClick={() => setFlagFilter(flag)}
            className={`text-xs font-medium px-2.5 py-1 rounded-full border transition-colors ${
              flagFilter === flag
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            {flag} ({flagCounts[flag] || 0})
          </button>
        ))}
      </div>

      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
            <tr>
              <th className="py-2.5 px-3 font-semibold">
                <button type="button" onClick={() => toggleSort('worker_id')} className="inline-flex items-center gap-1 hover:text-slate-900">
                  Worker ID <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold">Department</th>
              <th className="py-2.5 px-3 font-semibold text-right">
                <button type="button" onClick={() => toggleSort('assigned_count')} className="inline-flex items-center gap-1 hover:text-slate-900">
                  Assigned <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold text-right">
                <button type="button" onClick={() => toggleSort('completed_count')} className="inline-flex items-center gap-1 hover:text-slate-900">
                  Done <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold text-right">
                <button type="button" onClick={() => toggleSort('remaining_count')} className="inline-flex items-center gap-1 hover:text-slate-900">
                  Remaining <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold">
                <button type="button" onClick={() => toggleSort('completion_rate_pct')} className="inline-flex items-center gap-1 hover:text-slate-900">
                  Completion % <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold text-right">
                <button type="button" onClick={() => toggleSort('sla_compliance_pct')} className="inline-flex items-center gap-1 hover:text-slate-900">
                  SLA % <ArrowUpDown className="w-3 h-3" />
                </button>
              </th>
              <th className="py-2.5 px-3 font-semibold text-right">Z-Score</th>
              <th className="py-2.5 px-3 font-semibold">Primary Action Taken</th>
              <th className="py-2.5 px-3 font-semibold">Status Flag</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredWorkers.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-6 text-center text-slate-500">
                  No anonymized worker IDs match the current filter.
                </td>
              </tr>
            ) : (
              filteredWorkers.map((w) => {
                const isExpanded = expandedWorker === w.worker_id
                return (
                  <React.Fragment key={w.worker_id}>
                    <tr
                      onClick={() => setExpandedWorker(isExpanded ? null : w.worker_id)}
                      className="hover:bg-slate-50/90 cursor-pointer transition-colors"
                    >
                      <td className="py-2.5 px-3 font-mono font-semibold text-slate-900 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                          )}
                          {w.worker_id}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-700">{w.primary_category}</td>
                      <td className="py-2.5 px-3 text-right tabular-nums font-medium">{w.assigned_count}</td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-emerald-700 font-medium">
                        {w.completed_count}
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-amber-700 font-semibold">
                        {w.remaining_count}
                      </td>
                      <td className="py-2.5 px-3 min-w-[110px]">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                w.completion_rate_pct >= 85
                                  ? 'bg-emerald-500'
                                  : w.completion_rate_pct >= 68
                                  ? 'bg-blue-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${w.completion_rate_pct}%` }}
                            />
                          </div>
                          <span className="tabular-nums font-medium text-slate-700">
                            {w.completion_rate_pct}%
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums font-medium">
                        {w.sla_compliance_pct}%
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-slate-600">
                        {w.workload_z_score > 0 ? `+${w.workload_z_score}` : w.workload_z_score}
                      </td>
                      <td className="py-2.5 px-3 text-slate-700 max-w-[210px] truncate">
                        {w.primary_action}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded-full border text-[11px] font-medium ${
                            FLAG_STYLES[w.accountability_flag] || FLAG_STYLES['On Track']
                          }`}
                        >
                          {w.accountability_flag}
                        </span>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-slate-50/80">
                        <td colSpan={10} className="px-6 py-3">
                          <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
                            <div>
                              <span className="font-semibold text-slate-700">
                                Actions Taken Breakdown for {w.worker_id}:
                              </span>
                              <div className="flex flex-wrap gap-2 mt-1.5">
                                {(w.actions_summary || []).map((act) => (
                                  <span
                                    key={act.action}
                                    className="bg-white border border-slate-200 rounded-md px-2.5 py-1 text-slate-700"
                                  >
                                    {act.action}: <strong className="tabular-nums">{act.count}</strong>
                                  </span>
                                ))}
                              </div>
                            </div>
                            <div className="flex items-center gap-4 text-slate-600 tabular-nums">
                              <span>Avg Turnaround: <strong>{w.avg_resolution_hours}h</strong></span>
                              <span>Escalated Queue: <strong>{w.escalated_count}</strong></span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

