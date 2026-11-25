import React from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Building2, AlertTriangle } from 'lucide-react'

const ATTENTION_STYLES = {
  'Needs Immediate Attention': 'bg-rose-50 text-rose-700 border-rose-200',
  Watchlist: 'bg-amber-50 text-amber-700 border-amber-200',
  Healthy: 'bg-emerald-50 text-emerald-700 border-emerald-200',
}

export default function DepartmentPerformancePage({ analytics }) {
  if (!analytics || analytics.empty) return null
  const { departments = [] } = analytics

  return (
    <div className="space-y-5">
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <Building2 className="w-4 h-4 text-blue-600" />
          <h2 className="text-base font-semibold text-slate-900">
            Department Performance Intelligence &amp; Workload Benchmark
          </h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Compares resolution percentage, overdue backlogs, average resolution days, and top recorded delay causes across municipal departments.
        </p>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={departments} margin={{ top: 8, right: 16, left: -8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="department" tick={{ fontSize: 11, fill: '#334155' }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip contentStyle={{ borderRadius: '0.5rem', fontSize: '12px' }} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar yAxisId="left" dataKey="resolution_rate_pct" name="Resolution Rate %" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="right" dataKey="overdue" name="Overdue Count" fill="#dc2626" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Department Scorecard Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Department Accountability Scorecard</h3>
        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Department</th>
                <th className="py-2.5 px-3 text-right">Received</th>
                <th className="py-2.5 px-3 text-right">Resolved</th>
                <th className="py-2.5 px-3 text-right">Pending</th>
                <th className="py-2.5 px-3 text-right">Overdue</th>
                <th className="py-2.5 px-3 text-right">Resolution %</th>
                <th className="py-2.5 px-3 text-right">Avg Days</th>
                <th className="py-2.5 px-3">Most Common Recorded Delay Reasons</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {departments.map((d) => (
                <tr key={d.department} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-semibold text-slate-900">{d.department}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums">{d.total_received}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums text-emerald-700 font-medium">{d.resolved}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums text-amber-700 font-medium">{d.pending_backlog}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums text-rose-700 font-bold">{d.overdue}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums font-semibold">{d.resolution_rate_pct}%</td>
                  <td className="py-2.5 px-3 text-right tabular-nums">{d.avg_resolution_days}d</td>
                  <td className="py-2.5 px-3">
                    <div className="flex flex-wrap gap-1">
                      {(d.top_recorded_reasons || []).length > 0 ? (
                        d.top_recorded_reasons.map((r) => (
                          <span key={r.reason} className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[11px]">
                            {r.reason} ({r.count})
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-400 italic">None recorded</span>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[11px] font-medium ${ATTENTION_STYLES[d.attention_status]}`}>
                      {d.attention_status === 'Needs Immediate Attention' && <AlertTriangle className="w-3 h-3" />}
                      {d.attention_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

