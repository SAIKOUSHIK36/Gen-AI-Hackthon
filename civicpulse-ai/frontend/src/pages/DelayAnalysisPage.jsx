import React, { useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { AlertOctagon, CheckCircle2, HelpCircle, Search, Cpu } from 'lucide-react'

const EVIDENCE_BADGES = {
  RECORDED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  INFERRED_PATTERN: 'bg-amber-50 text-amber-700 border-amber-200',
  INSUFFICIENT_EVIDENCE: 'bg-slate-100 text-slate-700 border-slate-300',
}

export default function DelayAnalysisPage({ analytics }) {
  const [search, setSearch] = useState('')
  const [onlyOverdue, setOnlyOverdue] = useState(false)
  const [evidenceFilter, setEvidenceFilter] = useState('All')

  const { delay_analysis = {}, ml_anomalies = {}, pending_overdue_queue = [] } = analytics || {}

  const filteredQueue = useMemo(() => {
    const q = search.trim().toLowerCase()
    return pending_overdue_queue.filter((item) => {
      if (onlyOverdue && !item.is_overdue) return false
      if (evidenceFilter !== 'All' && item.evidence_type !== evidenceFilter) return false
      if (!q) return true
      return (
        item.complaint_id.toLowerCase().includes(q) ||
        item.department.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        item.delay_explanation.toLowerCase().includes(q)
      )
    })
  }, [pending_overdue_queue, search, onlyOverdue, evidenceFilter])

  if (!analytics || analytics.empty) return null

  const recordedReasons = delay_analysis.recorded_reasons || []
  const inferredPatterns = delay_analysis.inferred_patterns || []

  return (
    <div className="space-y-5">
      {/* Summary Evidence Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3.5">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-500">Delayed / Pending Analyzed</div>
          <div className="text-2xl font-bold text-slate-900 tabular-nums mt-1">
            {delay_analysis.total_delayed_or_pending}
          </div>
        </div>
        <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-emerald-800 font-medium">Confirmed Recorded Reasons</div>
          <div className="text-2xl font-bold text-emerald-900 tabular-nums mt-1">
            {delay_analysis.recorded_reason_cases}
          </div>
        </div>
        <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-amber-800 font-medium">Unrecorded (Pattern / Unconfirmed)</div>
          <div className="text-2xl font-bold text-amber-900 tabular-nums mt-1">
            {delay_analysis.unrecorded_reason_cases}
          </div>
        </div>
        <div className="bg-indigo-50/70 border border-indigo-200 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-indigo-800 font-medium">Isolation Forest Outliers</div>
          <div className="text-2xl font-bold text-indigo-900 tabular-nums mt-1">
            {ml_anomalies.flagged_delay_ticket_count || 0}
          </div>
        </div>
      </div>

      {/* Recorded Reasons vs Inferred Patterns */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-7 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-semibold text-slate-900">
              Confirmed Recorded Delay Reasons (Evidence: Delay_Reason Column)
            </h3>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Directly counted from uploaded Delay_Reason entries — zero speculation.
          </p>

          {recordedReasons.length > 0 ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={recordedReasons} layout="vertical" margin={{ top: 4, right: 20, left: 20, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis type="category" dataKey="reason" width={190} tick={{ fontSize: 11, fill: '#334155' }} />
                  <Tooltip contentStyle={{ borderRadius: '0.5rem', fontSize: '12px' }} />
                  <Bar dataKey="count" name="Delayed Cases" fill="#059669" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="p-6 bg-slate-50 border border-dashed border-slate-300 rounded-lg text-xs text-slate-600 text-center">
              {delay_analysis.insufficient_evidence_message}
            </div>
          )}
        </div>

        <div className="xl:col-span-5 bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
          <div>
            <div className="flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-semibold text-slate-900">
                Inferred Patterns &amp; Evidence Gaps (Unconfirmed)
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Explicitly separated from confirmed facts; never presented as verified causes when Delay_Reason is blank.
            </p>
          </div>

          <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
            {inferredPatterns.map((p) => (
              <div key={p.department} className="bg-amber-50/70 border border-amber-200 rounded-lg p-3 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-amber-900">{p.department}</span>
                  <span className="text-[10px] font-bold uppercase tracking-wide bg-amber-100 text-amber-800 px-2 py-0.5 rounded">
                    INFERRED PATTERN (UNCONFIRMED)
                  </span>
                </div>
                <p className="text-slate-700 leading-relaxed">{p.pattern_explanation}</p>
              </div>
            ))}

            {delay_analysis.insufficient_evidence_cases > 0 && (
              <div className="bg-slate-50 border border-slate-300 rounded-lg p-3 text-xs space-y-1">
                <div className="font-semibold text-slate-800">
                  Insufficient Data Cases ({delay_analysis.insufficient_evidence_cases})
                </div>
                <p className="text-slate-600 italic">{delay_analysis.insufficient_evidence_message}</p>
              </div>
            )}

            {inferredPatterns.length === 0 && delay_analysis.insufficient_evidence_cases === 0 && (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800">
                All delayed records in this slice have explicit recorded Delay_Reason values.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Overdue & Pending Delay Detection Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-600" />
              <h3 className="text-sm font-semibold text-slate-900">
                Delay Detection &amp; Pending/Overdue Complaint Queue
              </h3>
            </div>
            <p className="text-xs text-slate-500">
              Tracks Days Pending, Days Overdue, Expected Deadline, Evidence Type, and Scikit-learn Isolation Forest Flags.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search ID, dept, reason..."
                className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg"
              />
            </div>

            <select
              value={evidenceFilter}
              onChange={(e) => setEvidenceFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white"
            >
              <option value="All">All Evidence Types</option>
              <option value="RECORDED">Recorded Only</option>
              <option value="INFERRED_PATTERN">Inferred Pattern</option>
              <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence</option>
            </select>

            <label className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-rose-50 border border-rose-200 px-2.5 py-1.5 rounded-lg cursor-pointer">
              <input
                type="checkbox"
                checked={onlyOverdue}
                onChange={(e) => setOnlyOverdue(e.target.checked)}
                className="rounded border-rose-300 text-rose-600"
              />
              Crossed Deadline Only
            </label>
          </div>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Complaint ID</th>
                <th className="py-2.5 px-3">Department</th>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3">Priority</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Deadline</th>
                <th className="py-2.5 px-3 text-right">Pending</th>
                <th className="py-2.5 px-3 text-right">Overdue</th>
                <th className="py-2.5 px-3">Evidence</th>
                <th className="py-2.5 px-3">Delay Reason / Assessment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredQueue.slice(0, 60).map((item) => (
                <tr key={item.complaint_id} className={item.is_overdue ? 'bg-rose-50/30 hover:bg-rose-50/60' : 'hover:bg-slate-50'}>
                  <td className="py-2.5 px-3 font-mono font-semibold whitespace-nowrap">
                    {item.complaint_id}
                    {item.is_ml_anomaly && (
                      <span
                        title="Flagged by Scikit-learn Isolation Forest"
                        className="ml-1.5 inline-flex items-center gap-0.5 text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded"
                      >
                        <Cpu className="w-2.5 h-2.5" /> ML
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-slate-700">{item.department}</td>
                  <td className="py-2.5 px-3 text-slate-700">{item.category}</td>
                  <td className="py-2.5 px-3 font-medium">{item.priority}</td>
                  <td className="py-2.5 px-3">{item.status}</td>
                  <td className="py-2.5 px-3 tabular-nums">{item.deadline}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums">{item.days_pending}d</td>
                  <td className="py-2.5 px-3 text-right tabular-nums font-bold text-rose-700">
                    {item.is_overdue ? `${item.days_overdue}d` : '—'}
                  </td>
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <span className={`text-[10px] font-semibold border px-2 py-0.5 rounded-full ${EVIDENCE_BADGES[item.evidence_type]}`}>
                      {item.evidence_type}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700 max-w-xs">{item.delay_explanation}</td>
                </tr>
              ))}
              {filteredQueue.length === 0 && (
                <tr>
                  <td colSpan={10} className="py-6 text-center text-slate-500">
                    No pending or overdue complaints match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

