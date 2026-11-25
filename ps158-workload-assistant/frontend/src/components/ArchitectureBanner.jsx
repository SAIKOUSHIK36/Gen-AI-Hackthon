import React from 'react'
import { ShieldCheck, Database, Cpu, Sparkles, ArrowRight, Lock } from 'lucide-react'

export default function ArchitectureBanner({ piiAudit, analyticsReady, narrativeReady, onOpenAudit }) {
  const droppedCount = piiAudit?.dropped_pii_columns?.length ?? 0
  const scrubbedCount = piiAudit?.total_inline_pii_scrubbed ?? 0

  const layers = [
    {
      num: 'L1',
      name: 'Ingestion & Filters',
      desc: 'CSV / JSON / 640+ Row Demo',
      icon: Database,
      active: Boolean(piiAudit),
      tone: 'bg-blue-50 text-blue-700 border-blue-200',
    },
    {
      num: 'L2',
      name: 'Zero-PII Shield',
      desc: piiAudit
        ? `${droppedCount} cols dropped · ${scrubbedCount} inline scrubbed`
        : 'Strips Citizen PII & Hashes Staff',
      icon: ShieldCheck,
      active: Boolean(piiAudit),
      tone: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      clickable: Boolean(piiAudit),
    },
    {
      num: 'L3',
      name: 'Pandas & NumPy Engine',
      desc: analyticsReady ? 'KPIs, Trends & Worker Z-Scores' : 'Aggregates Anonymized Metrics',
      icon: Cpu,
      active: analyticsReady,
      tone: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    },
    {
      num: 'L4',
      name: 'Gemini + Guardrails',
      desc: narrativeReady ? 'Executive Report Verified' : 'Strict Aggregated Payload Only',
      icon: Sparkles,
      active: narrativeReady,
      tone: 'bg-violet-50 text-violet-700 border-violet-200',
    },
  ]

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center gap-2">
          <Lock className="w-4 h-4 text-emerald-600" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            4-Layer Privacy-Preserving Pipeline Architecture
          </span>
        </div>
        {piiAudit && (
          <button
            type="button"
            onClick={onOpenAudit}
            className="text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-full transition-colors"
          >
            Inspect Layer 2 PII Audit Receipt →
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 items-stretch">
        {layers.map((layer, idx) => {
          const Icon = layer.icon
          const Wrapper = layer.clickable ? 'button' : 'div'
          return (
            <div key={layer.num} className="flex items-center gap-2">
              <Wrapper
                type={layer.clickable ? 'button' : undefined}
                onClick={layer.clickable ? onOpenAudit : undefined}
                className={`flex-1 text-left rounded-lg border px-3 py-2 transition-all ${
                  layer.active ? layer.tone : 'bg-slate-50 text-slate-500 border-slate-200'
                } ${layer.clickable ? 'hover:shadow-sm cursor-pointer' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold tracking-wide uppercase opacity-80">
                    Layer {layer.num.slice(1)}
                  </span>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="font-semibold text-sm leading-tight mt-0.5">{layer.name}</div>
                <div className="text-[11px] opacity-85 mt-0.5 truncate">{layer.desc}</div>
              </Wrapper>
              {idx < layers.length - 1 && (
                <ArrowRight className="hidden lg:block w-4 h-4 text-slate-300 shrink-0" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

