import React from 'react'
import {
  ClipboardList,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Users,
  ShieldCheck,
} from 'lucide-react'

export default function KpiCards({ kpis, piiAudit, onOpenAudit }) {
  if (!kpis) return null

  const compPct = kpis.completion_rate_pct ?? 0
  const droppedCols = piiAudit?.dropped_pii_columns?.length ?? 0
  const scrubbedInline = piiAudit?.total_inline_pii_scrubbed ?? 0

  const cards = [
    {
      title: 'Total Service Requests',
      value: kpis.total_requests?.toLocaleString() ?? '0',
      sub:
        kpis.date_range?.start && kpis.date_range?.end
          ? `${kpis.date_range.start} → ${kpis.date_range.end}`
          : 'No date span',
      icon: ClipboardList,
      accent: 'text-blue-600 bg-blue-50',
    },
    {
      title: 'Completed vs. Remaining',
      value: `${kpis.completed_count?.toLocaleString() ?? 0} / ${kpis.remaining_count?.toLocaleString() ?? 0}`,
      sub: `${compPct}% completion rate (${kpis.escalated_count ?? 0} escalated)`,
      icon: CheckCircle2,
      accent: 'text-emerald-600 bg-emerald-50',
      progress: compPct,
    },
    {
      title: 'SLA Compliance Rate',
      value: `${kpis.sla_compliance_pct ?? 0}%`,
      sub: `${kpis.overdue_remaining_count ?? 0} open overdue · ${kpis.sla_breach_count ?? 0} total breaches`,
      icon: AlertTriangle,
      accent:
        (kpis.sla_compliance_pct ?? 0) >= 80
          ? 'text-emerald-600 bg-emerald-50'
          : 'text-amber-600 bg-amber-50',
    },
    {
      title: 'Resolution Velocity',
      value: `${kpis.avg_resolution_hours ?? 0}h`,
      sub: `Median ${kpis.median_resolution_hours ?? 0}h · P90 ${kpis.p90_resolution_hours ?? 0}h`,
      icon: Clock,
      accent: 'text-indigo-600 bg-indigo-50',
    },
    {
      title: 'Anonymized Staff Roster',
      value: `${kpis.active_worker_count ?? 0} IDs`,
      sub: `Backlog/Throughput ratio: ${kpis.backlog_to_throughput_ratio ?? 0}x`,
      icon: Users,
      accent: 'text-slate-700 bg-slate-100',
    },
    {
      title: 'Layer 2 PII Shield',
      value: piiAudit?.post_shield_pii_leaks_detected === 0 ? '0 PII Leaks' : 'Check Audit',
      sub: `${droppedCols} columns dropped · ${scrubbedInline} inline scrubbed`,
      icon: ShieldCheck,
      accent: 'text-emerald-700 bg-emerald-50',
      onClick: onOpenAudit,
    },
  ]

  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
      {cards.map((card) => {
        const Icon = card.icon
        const Tag = card.onClick ? 'button' : 'div'
        return (
          <Tag
            key={card.title}
            type={card.onClick ? 'button' : undefined}
            onClick={card.onClick}
            className={`bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-left flex flex-col justify-between ${
              card.onClick ? 'hover:border-emerald-400 hover:shadow transition-all cursor-pointer' : ''
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-medium text-slate-500 leading-snug">{card.title}</span>
              <span className={`p-1.5 rounded-lg shrink-0 ${card.accent}`}>
                <Icon className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-2.5">
              <div className="text-xl font-bold text-slate-900 tabular-nums tracking-tight">
                {card.value}
              </div>
              {typeof card.progress === 'number' && (
                <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden mt-2">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all"
                    style={{ width: `${Math.min(100, Math.max(0, card.progress))}%` }}
                  />
                </div>
              )}
              <div className="text-[11px] text-slate-500 mt-1.5 leading-snug">{card.sub}</div>
            </div>
          </Tag>
        )
      })}
    </section>
  )
}

