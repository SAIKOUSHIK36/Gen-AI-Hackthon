import React from 'react'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { CheckCircle2, Clock } from 'lucide-react'

const STATUS_COLORS = ['#10b981', '#f59e0b', '#3b82f6', '#e11d48', '#64748b']

export default function ResolutionAnalysisPage({ analytics }) {
  if (!analytics || analytics.empty) return null

  const { kpis, status_breakdown = [], departments = [], categories = [] } = analytics

  return (
    <div className="space-y-5">
      {/* Resolution vs Pending Rate Banner */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Resolution Rate</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-bold text-slate-900 tabular-nums mt-2">
            {kpis.resolution_rate_pct}%
          </div>
          <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden mt-3">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${kpis.resolution_rate_pct}%` }} />
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {kpis.resolved_count} resolved out of {kpis.total_received} total complaints ({kpis.rejected_count} rejected).
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-amber-700">Pending &amp; Active Backlog Rate</span>
            <Clock className="w-5 h-5 text-amber-600" />
          </div>
          <div className="text-3xl font-bold text-slate-900 tabular-nums mt-2">
            {kpis.pending_rate_pct}%
          </div>
          <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden mt-3">
            <div className="h-full bg-amber-500 rounded-full" style={{ width: `${kpis.pending_rate_pct}%` }} />
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {kpis.total_pending_backlog} unresolved complaints ({kpis.pending_status_count} Pending, {kpis.in_progress_count} In Progress, {kpis.overdue_count} crossed deadline).
          </p>
        </div>
      </div>

      {/* Status Distribution + Department Comparison */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-5 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">Status Distribution</h3>
          <p className="text-xs text-slate-500 mb-3">Resolved, Pending, In Progress, Overdue, and Rejected</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={status_breakdown}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  innerRadius={52}
                  outerRadius={88}
                  paddingAngle={2}
                >
                  {status_breakdown.map((entry, idx) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[idx % STATUS_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: '0.5rem', fontSize: '12px' }} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="xl:col-span-7 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">Department Resolution Comparison</h3>
          <p className="text-xs text-slate-500 mb-3">Resolved vs. Pending vs. Rejected volume per department</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={departments} margin={{ top: 8, right: 12, left: -10, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="department" tick={{ fontSize: 11, fill: '#475569' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip contentStyle={{ borderRadius: '0.5rem', fontSize: '12px' }} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="resolved" name="Resolved" stackId="s" fill="#10b981" />
                <Bar dataKey="pending_backlog" name="Pending/In Progress" stackId="s" fill="#f59e0b" />
                <Bar dataKey="rejected" name="Rejected" stackId="s" fill="#64748b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Category Comparison Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Category-Wise Resolution &amp; Delay Comparison</h3>
        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3 text-right">Received</th>
                <th className="py-2.5 px-3 text-right">Resolved</th>
                <th className="py-2.5 px-3 text-right">Pending</th>
                <th className="py-2.5 px-3 text-right">Overdue</th>
                <th className="py-2.5 px-3 text-right">Resolution %</th>
                <th className="py-2.5 px-3 text-right">Avg Resolution Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {categories.map((c) => (
                <tr key={c.category} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-medium text-slate-900">{c.category}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums">{c.total_received}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums text-emerald-700 font-medium">{c.resolved}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums text-amber-700 font-medium">{c.pending_backlog}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums text-rose-700 font-semibold">{c.overdue}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums font-semibold">{c.resolution_rate_pct}%</td>
                  <td className="py-2.5 px-3 text-right tabular-nums">{c.avg_resolution_days} days</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

