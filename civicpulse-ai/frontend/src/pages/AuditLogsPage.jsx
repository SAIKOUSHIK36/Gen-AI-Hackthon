import React, { useState } from 'react'
import { ScrollText, RefreshCw } from 'lucide-react'

const EVENT_COLORS = {
  DATASET_INGESTED: 'bg-blue-50 text-blue-700 border-blue-200',
  ML_ANOMALY_SCAN: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  AI_QA_QUERY: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  REPORT_GENERATED: 'bg-violet-50 text-violet-700 border-violet-200',
  PDF_EXPORTED: 'bg-slate-100 text-slate-700 border-slate-300',
}

export default function AuditLogsPage({ logs = [], onRefresh }) {
  const [filterType, setFilterType] = useState('All')

  const filtered = logs.filter((l) => filterType === 'All' || l.event_type === filterType)

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <ScrollText className="w-5 h-5 text-slate-700" />
            <h2 className="text-base font-semibold text-slate-900">SQLite System Audit &amp; Privacy Trail</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable operational history of dataset uploads, Zero-PII scrubbing, Isolation Forest scans, AI queries, and PDF exports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white"
          >
            <option value="All">All Event Types</option>
            <option value="DATASET_INGESTED">DATASET_INGESTED</option>
            <option value="ML_ANOMALY_SCAN">ML_ANOMALY_SCAN</option>
            <option value="AI_QA_QUERY">AI_QA_QUERY</option>
            <option value="REPORT_GENERATED">REPORT_GENERATED</option>
            <option value="PDF_EXPORTED">PDF_EXPORTED</option>
          </select>
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
            <tr>
              <th className="py-2.5 px-3">Timestamp (UTC)</th>
              <th className="py-2.5 px-3">Event Type</th>
              <th className="py-2.5 px-3">Actor / Engine</th>
              <th className="py-2.5 px-3">Session</th>
              <th className="py-2.5 px-3">Summary</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((log) => (
              <tr key={log.id} className="hover:bg-slate-50">
                <td className="py-2.5 px-3 tabular-nums text-slate-500 whitespace-nowrap">
                  {log.created_at?.replace('T', ' ').slice(0, 19)}
                </td>
                <td className="py-2.5 px-3 whitespace-nowrap">
                  <span className={`text-[10px] font-semibold border px-2 py-0.5 rounded-full ${EVENT_COLORS[log.event_type] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                    {log.event_type}
                  </span>
                </td>
                <td className="py-2.5 px-3 font-medium text-slate-700">{log.actor}</td>
                <td className="py-2.5 px-3 font-mono text-slate-500">{log.session_id || '—'}</td>
                <td className="py-2.5 px-3 text-slate-800">{log.summary}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-slate-500">
                  No audit log entries recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

