import React from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from 'recharts'
import { TrendingUp, Layers, Activity } from 'lucide-react'

const PRIORITY_COLORS = {
  Critical: '#dc2626',
  High: '#f97316',
  Medium: '#3b82f6',
  Low: '#64748b',
}

export default function WorkloadCharts({ analytics }) {
  if (!analytics || analytics.empty) return null

  const {
    time_series = [],
    trend_metrics = {},
    categories = [],
    priority_breakdown = [],
    actions_rollup = [],
  } = analytics

  const shortCategories = categories.map((c) => ({
    ...c,
    shortName: c.service_category.replace(' & ', ' & ').split(' ').slice(0, 2).join(' '),
  }))

  return (
    <section className="grid grid-cols-1 xl:grid-cols-12 gap-4">
      {/* Time-Period Completed vs Remaining + Cumulative Backlog */}
      <div className="xl:col-span-7 bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col">
        <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
          <div>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-900">
                Workload Velocity by {trend_metrics.granularity === 'month' ? 'Month' : 'Week'} (Completed vs. Remaining)
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Aggregated from sanitized timestamps · Cumulative open backlog overlay
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            <span className="px-2 py-1 rounded-md bg-slate-100 text-slate-700 font-medium tabular-nums">
              Intake slope: {trend_metrics.intake_slope_per_period > 0 ? '+' : ''}
              {trend_metrics.intake_slope_per_period ?? 0}/period
            </span>
            <span className="px-2 py-1 rounded-md bg-blue-50 text-blue-700 font-medium tabular-nums">
              Next {trend_metrics.granularity || 'period'} forecast: ~{trend_metrics.projected_next_period_requests ?? 0}
            </span>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={time_series} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickMargin={6}
                minTickGap={18}
              />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#cbd5e1',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar yAxisId="left" dataKey="completed" name="Completed" stackId="workload" fill="#10b981" radius={[0, 0, 0, 0]} />
              <Bar yAxisId="left" dataKey="remaining" name="Remaining Open" stackId="workload" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cumulative_backlog"
                name="Cumulative Backlog"
                stroke="#1d4ed8"
                strokeWidth={2.2}
                dot={{ r: 2.5 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Service Category Workload Breakdown */}
      <div className="xl:col-span-5 bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-600" />
              <h2 className="text-sm font-semibold text-slate-900">
                Service Category Workload &amp; SLA
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Completed vs. remaining volume across municipal departments
            </p>
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={shortCategories}
              layout="vertical"
              margin={{ top: 4, right: 18, left: 10, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis
                type="category"
                dataKey="shortName"
                width={108}
                tick={{ fontSize: 11, fill: '#334155' }}
              />
              <Tooltip
                formatter={(value, name) => [value, name]}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.service_category || ''}
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#cbd5e1',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="completed" name="Completed" stackId="cat" fill="#059669" />
              <Bar dataKey="remaining" name="Remaining" stackId="cat" fill="#f97316" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Operational Actions Taken & Priority Distribution */}
      <div className="xl:col-span-7 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-4 h-4 text-emerald-600" />
          <h2 className="text-sm font-semibold text-slate-900">
            Standardized Actions Taken &amp; Closure Yield
          </h2>
        </div>
        <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
          {actions_rollup.slice(0, 8).map((item) => (
            <div key={item.action_taken} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-700 truncate pr-3">{item.action_taken}</span>
                <span className="text-slate-500 tabular-nums shrink-0">
                  {item.completed}/{item.count} done ({item.completion_rate_pct}%)
                </span>
              </div>
              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden flex">
                <div
                  className="bg-emerald-500 h-full"
                  style={{ width: `${item.completion_rate_pct}%` }}
                />
                <div
                  className="bg-amber-400 h-full"
                  style={{ width: `${100 - item.completion_rate_pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="xl:col-span-5 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-1">
          Category SLA Compliance &amp; Priority Mix
        </h2>
        <p className="text-xs text-slate-500 mb-3">
          Department turnaround vs. SLA targets &amp; urgency breakdown
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
          {priority_breakdown.map((p) => (
            <div key={p.priority} className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2">
              <div className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: PRIORITY_COLORS[p.priority] || '#64748b' }}
                />
                <span className="text-[11px] font-semibold text-slate-600">{p.priority}</span>
              </div>
              <div className="text-sm font-bold text-slate-900 tabular-nums mt-0.5">
                {p.count} <span className="text-[11px] font-normal text-slate-500">({p.pct}%)</span>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
          {categories.map((c) => (
            <div
              key={c.service_category}
              className="flex items-center justify-between text-xs border border-slate-100 rounded-lg px-2.5 py-1.5 bg-slate-50/70"
            >
              <span className="font-medium text-slate-700 truncate pr-2">{c.service_category}</span>
              <div className="flex items-center gap-3 shrink-0 tabular-nums">
                <span className="text-slate-500">{c.avg_resolution_hours}h avg</span>
                <span
                  className={`font-semibold px-1.5 py-0.5 rounded ${
                    c.sla_compliance_pct >= 80
                      ? 'bg-emerald-50 text-emerald-700'
                      : c.sla_compliance_pct >= 65
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-rose-50 text-rose-700'
                  }`}
                >
                  {c.sla_compliance_pct}% SLA
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

