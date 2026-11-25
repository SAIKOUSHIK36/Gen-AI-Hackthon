import React, { useState } from 'react'
import { FileText, FileDown, Sparkles, History, ShieldCheck } from 'lucide-react'

export default function ReportsPage({
  activeReport,
  savedReports = [],
  generating,
  exportingPdf,
  onGenerateReport,
  onDownloadPdf,
  onSelectSavedReport,
}) {
  const [title, setTitle] = useState('CivicPulse Executive Delay & Resolution Briefing')
  const [focusPrompt, setFocusPrompt] = useState('')

  const report = activeReport?.report_bundle?.report
  const mode = activeReport?.report_bundle?.mode

  return (
    <div className="space-y-5">
      {/* Generator Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-violet-600" />
              <h2 className="text-base font-semibold text-slate-900">AI Administrative Reports &amp; PDF Export</h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Synthesizes Python-verified counts, department scorecards, recorded vs. inferred delay causes, and actionable recommendations.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={generating}
              onClick={() => onGenerateReport({ title, focusPrompt })}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50 px-4 py-2 rounded-lg"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {generating ? 'Generating Report...' : 'Generate AI Report'}
            </button>
            {activeReport && (
              <button
                type="button"
                disabled={exportingPdf}
                onClick={() => onDownloadPdf({ reportId: activeReport.report_id, reportBundle: activeReport.report_bundle })}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 px-4 py-2 rounded-lg"
              >
                <FileDown className="w-3.5 h-3.5" />
                {exportingPdf ? 'Building PDF...' : 'Download PDF'}
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Report Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-600 mb-1">Administrative Focus (Optional)</label>
            <input
              type="text"
              value={focusPrompt}
              onChange={(e) => setFocusPrompt(e.target.value)}
              placeholder="e.g., Focus on Roads Dept material shortages and overdue Water complaints"
              className="w-full border border-slate-200 rounded-lg px-3 py-2"
            />
          </div>
        </div>
      </div>

      {/* Rendered Report Preview */}
      {report && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-base font-bold text-slate-900">{activeReport.title || title}</h3>
              <span className="text-xs text-slate-500">
                Report ID: <code className="font-mono">{activeReport.report_id}</code> · Mode:{' '}
                {mode === 'gemini_live' ? `Google Gemini (${activeReport.report_bundle.model})` : 'Data-Grounded Deterministic Engine'}
              </span>
            </div>
            <span className="inline-flex items-center gap-1 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full">
              <ShieldCheck className="w-3.5 h-3.5" /> Zero PII &amp; Grounded
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs">
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1.5">
              <div className="font-bold uppercase tracking-wider text-blue-700">Executive Summary</div>
              <p className="text-sm text-slate-800 leading-relaxed">{report.executive_summary}</p>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1.5">
              <div className="font-bold uppercase tracking-wider text-indigo-700">Department Performance Intelligence</div>
              <p className="text-sm text-slate-800 leading-relaxed">{report.department_performance_narrative}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-xs">
            <div className="border border-slate-200 rounded-xl p-4 space-y-2">
              <div className="font-bold uppercase tracking-wider text-emerald-700">Recorded Delay Findings (Confirmed)</div>
              {(report.recorded_delay_findings || []).map((item, i) => (
                <div key={i} className="bg-emerald-50/50 border border-emerald-200 rounded-lg p-2.5">
                  <div className="font-semibold text-slate-900">{item.reason}</div>
                  <div className="text-slate-600 mt-0.5">{item.evidence}</div>
                </div>
              ))}
            </div>

            <div className="border border-slate-200 rounded-xl p-4 space-y-2">
              <div className="font-bold uppercase tracking-wider text-amber-700">Inferred Delay Patterns &amp; Gaps (Unconfirmed)</div>
              {(report.inferred_delay_patterns || []).map((item, i) => (
                <div key={i} className="bg-amber-50/50 border border-amber-200 rounded-lg p-2.5">
                  <div className="font-semibold text-slate-900">
                    {item.department} <span className="text-[10px] uppercase text-amber-700">({item.evidence_type})</span>
                  </div>
                  <div className="text-slate-700 mt-0.5">{item.explanation}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2 text-xs">
            <div className="font-bold uppercase tracking-wider text-violet-700">Administrative Recommendations (Suggestions)</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {(report.administrative_recommendations || []).map((r, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-lg p-3">
                  <span className="inline-block text-[10px] font-bold uppercase bg-violet-50 text-violet-700 px-2 py-0.5 rounded mb-1">
                    {r.priority}
                  </span>
                  <div className="font-medium text-slate-900">{r.recommendation}</div>
                  <div className="text-slate-500 mt-1">Evidence basis: {r.basis}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SQLite Report History */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <History className="w-4 h-4 text-slate-600" />
          <h3 className="text-sm font-semibold text-slate-900">Saved Report History (SQLite)</h3>
        </div>
        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="py-2 px-3">Report ID</th>
                <th className="py-2 px-3">Title</th>
                <th className="py-2 px-3">Source Dataset</th>
                <th className="py-2 px-3">Engine</th>
                <th className="py-2 px-3">Created UTC</th>
                <th className="py-2 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {savedReports.map((sr) => (
                <tr key={sr.report_id} className="hover:bg-slate-50">
                  <td className="py-2 px-3 font-mono font-semibold">{sr.report_id}</td>
                  <td className="py-2 px-3 font-medium text-slate-900">{sr.title}</td>
                  <td className="py-2 px-3 text-slate-600">{sr.source_name}</td>
                  <td className="py-2 px-3">{sr.model_name}</td>
                  <td className="py-2 px-3 tabular-nums text-slate-500">{sr.created_at?.slice(0, 19)}</td>
                  <td className="py-2 px-3 text-right space-x-2">
                    <button
                      type="button"
                      onClick={() => onSelectSavedReport(sr)}
                      className="text-blue-600 hover:underline font-medium"
                    >
                      View
                    </button>
                    <button
                      type="button"
                      onClick={() => onDownloadPdf({ reportId: sr.report_id })}
                      className="text-slate-700 hover:underline font-medium"
                    >
                      PDF
                    </button>
                  </td>
                </tr>
              ))}
              {savedReports.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-5 text-center text-slate-500">
                    No saved reports yet. Click Generate AI Report above to store one in SQLite.
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

