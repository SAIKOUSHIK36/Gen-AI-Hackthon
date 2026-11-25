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
} from 'recharts'
import {
  Inbox,
  CheckCircle2,
  Clock,
  Loader2,
  AlertTriangle,
  Percent,
  Timer,
  Cpu,
  ArrowRight,
  Building2,
} from 'lucide-react'

export default function DashboardPage({ analytics, onNavigate }) {
  if (!analytics || analytics.empty) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-slate-500">
        No records match the current filter selection. Reset filters or upload a dataset.
      </div>
    )
  }

  const { kpis, time_series = [], departments = [], delay_analysis = {}, ml_anomalies = {} } = analytics
  const topDept = departments[0]
  const topReason = delay_analysis.recorded_reasons?.[0]

  const cards = [
    {
      label: 'Total Complaints Received',
      value: kpis.total_received?.toLocaleString() ?? 0,
      sub: `${kpis.date_range?.start} → ${kpis.date_range?.end}`,
      icon: Inbox,
      tone: 'bg-blue-50 text-blue-600',
    },
    {
      label: 'Resolved Complaints',
      value: kpis.resolved_count?.toLocaleString() ?? 0,
      sub: `${kpis.resolution_rate_pct}% resolution rate`,
      icon: CheckCircle2,
      tone: 'bg-emerald-50 text-emerald-600',
    },
    {
      label: 'Pending Backlog',
      value: kpis.total_pending_backlog?.toLocaleString() ?? 0,
      sub: `${kpis.pending_status_count} Pending · ${kpis.in_progress_count} In Progress`,
      icon: Clock,
      tone: 'bg-amber-50 text-amber-600',
    },
    {
      label: 'In Progress',
      value: kpis.in_progress_count?.toLocaleString() ?? 0,
      sub: `${kpis.high_priority_pending} high/critical unresolved`,
      icon: Loader2,
      tone: 'bg-indigo-50 text-indigo-600',
    },
    {
      label: 'Overdue (Crossed Deadline)',
      value: kpis.overdue_count?.toLocaleString() ?? 0,
      sub: `${kpis.departments_needing_attention} dept(s) need attention`,
      icon: AlertTriangle,
      tone: 'bg-rose-50 text-rose-600',
    },
    {
      label: 'Avg Resolution Time',
      value: `${kpis.avg_resolution_days ?? 0}d`,
      sub: `Median ${kpis.median_resolution_days ?? 0} days`,
      icon: Timer,
      tone: 'bg-slate-100 text-slate-700',
    },
  ]

  return (
    <div className="space-y-5">
      {/* 5 Core Administrative Questions Strip */}
      <div className="bg-gradient-to-r from-slate-900 to-blue-950 text-white rounded-2xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <h2 className="text-base font-semibold">Executive Administrative Pulse</h2>
            <p className="text-xs text-slate-300">
              Instant answers to the 5 core governance questions calculated deterministically from your dataset.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('ask')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold bg-blue-500 hover:bg-blue-400 text-white px-3.5 py-2 rounded-lg transition-colors"
          >
            Ask CivicPulse AI <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
          <div className="bg-white/10 rounded-xl p-3 border border-white/10">
            <div className="text-slate-300">1. Received</div>
            <div className="text-lg font-bold tabular-nums mt-0.5">{kpis.total_received}</div>
          </div>
          <div className="bg-white/10 rounded-xl p-3 border border-white/10">
            <div className="text-slate-300">2. Resolved</div>
            <div className="text-lg font-bold text-emerald-300 tabular-nums mt-0.5">
              {kpis.resolved_count} ({kpis.resolution_rate_pct}%)
            </div>
          </div>
          <div className="bg-white/10 rounded-xl p-3 border border-white/10">
            <div className="text-slate-300">3. Pending / Overdue</div>
            <div className="text-lg font-bold text-amber-300 tabular-nums mt-0.5">
              {kpis.total_pending_backlog} ({kpis.overdue_count} overdue)
            </div>
          </div>
          <div className="bg-white/10 rounded-xl p-3 border border-white/10">
            <div className="text-slate-300">4. Top Recorded Delay</div>
            <div className="text-sm font-semibold text-white mt-1 truncate">
              {topReason ? `${topReason.reason} (${topReason.count})` : 'Insufficient evidence'}
            </div>
          </div>
          <div className="bg-white/10 rounded-xl p-3 border border-white/10">
            <div className="text-slate-300">5. Priority Focus Dept</div>
            <div className="text-sm font-semibold text-rose-300 mt-1 truncate">
              {topDept ? `${topDept.department} (${topDept.overdue} overdue)` : 'N/A'}
            </div>
          </div>
        </div>
      </div>

      {/* Statistic Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
        {cards.map((c) => {
          const Icon = c.icon
          return (
            <div key={c.label} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col justify-between">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-medium text-slate-500">{c.label}</span>
                <span className={`p-1.5 rounded-lg ${c.tone}`}>
                  <Icon className="w-4 h-4" />
                </span>
              </div>
              <div className="mt-2.5">
                <div className="text-2xl font-bold text-slate-900 tabular-nums">{c.value}</div>
                <div className="text-[11px] text-slate-500 mt-1">{c.sub}</div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-7 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Complaint Intake vs. Resolution &amp; Overdue Trend</h3>
              <p className="text-xs text-slate-500">
                Scikit-learn Isolation Forest monitors volume spikes ({ml_anomalies.volume_anomaly_periods?.length || 0} flagged)
              </p>
            </div>
            <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 px-2.5 py-1 rounded-full">
              <Cpu className="w-3.5 h-3.5" />
              {ml_anomalies.flagged_delay_ticket_count || 0} ML Delay Outliers
            </span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={time_series} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#64748b' }} minTickGap={16} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip contentStyle={{ borderRadius: '0.5rem', fontSize: '12px' }} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="resolved" name="Resolved" stackId="a" fill="#10b981" />
                <Bar dataKey="pending" name="Pending Backlog" stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Line type="monotone" dataKey="overdue" name="Overdue" stroke="#e11d48" strokeWidth={2.2} dot={{ r: 2.5 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="xl:col-span-5 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Department Workload &amp; Overdue Comparison</h3>
              <p className="text-xs text-slate-500">Departments sorted by highest overdue backlog</p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('departments')}
              className="text-xs font-medium text-blue-600 hover:text-blue-800"
            >
              Details →
            </button>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={departments} layout="vertical" margin={{ top: 4, right: 16, left: 10, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis type="category" dataKey="department" width={118} tick={{ fontSize: 11, fill: '#334155' }} />
                <Tooltip contentStyle={{ borderRadius: '0.5rem', fontSize: '12px' }} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="resolved" name="Resolved" stackId="d" fill="#059669" />
                <Bar dataKey="pending_backlog" name="Pending" stackId="d" fill="#f59e0b" />
                <Bar dataKey="overdue" name="Overdue" fill="#dc2626" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button
          type="button"
          onClick={() => onNavigate('delays')}
          className="bg-white border border-slate-200 hover:border-blue-400 rounded-xl p-4 text-left shadow-sm transition-all"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-600">Delay Intelligence</span>
            <ArrowRight className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-sm font-semibold text-slate-900 mt-1">
            Inspect {kpis.overdue_count} Overdue Complaints &amp; Root Causes
          </div>
          <p className="text-xs text-slate-500 mt-1">
            View recorded Delay_Reason evidence separated cleanly from unconfirmed inferred patterns.
          </p>
        </button>

        <button
          type="button"
          onClick={() => onNavigate('departments')}
          className="bg-white border border-slate-200 hover:border-blue-400 rounded-xl p-4 text-left shadow-sm transition-all"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-600">Department Intelligence</span>
            <Building2 className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-sm font-semibold text-slate-900 mt-1">
            {kpis.departments_needing_attention} Department(s) Flagged for Attention
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Compare average resolution days, resolution rates, and recurring departmental bottlenecks.
          </p>
        </button>

        <button
          type="button"
          onClick={() => onNavigate('reports')}
          className="bg-white border border-slate-200 hover:border-blue-400 rounded-xl p-4 text-left shadow-sm transition-all"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-violet-600">Executive PDF Briefing</span>
            <Percent className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-sm font-semibold text-slate-900 mt-1">
            Generate AI Administrative Report &amp; PDF
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Synthesize Gemini narrative explanations, recommendations, and export ReportLab PDF.
          </p>
        </button>
      </div>
    </div>
  )
}

