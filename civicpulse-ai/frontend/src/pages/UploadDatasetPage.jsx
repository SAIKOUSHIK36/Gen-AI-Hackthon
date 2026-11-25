import React, { useRef, useState } from 'react'
import { Upload, Database, Download, ShieldCheck, CheckCircle2, Trash2, FileSpreadsheet } from 'lucide-react'
import { getSampleCsvDownloadUrl } from '../api'

export default function UploadDatasetPage({
  loading,
  sourceName,
  piiReceipt,
  previewRows = [],
  onLoadSample,
  onUploadFile,
}) {
  const fileRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)
  const [rowsCount, setRowsCount] = useState(620)
  const [injectPii, setInjectPii] = useState(true)

  const handleFiles = (files) => {
    const file = files?.[0]
    if (file) onUploadFile(file)
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* CSV & Excel Dropzone */}
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragActive(true)
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragActive(false)
            handleFiles(e.dataTransfer.files)
          }}
          onClick={() => fileRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click()
          }}
          className={`lg:col-span-7 bg-white border-2 border-dashed rounded-2xl p-6 cursor-pointer transition-colors flex flex-col justify-center ${
            dragActive ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 hover:border-blue-400'
          }`}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={(e) => {
              handleFiles(e.target.files)
              e.target.value = ''
            }}
          />
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <Upload className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Upload Complaint Dataset (CSV or Excel .xlsx / .xls)
              </h2>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Supports canonical CivicPulse columns (<code className="font-mono bg-slate-100 px-1 rounded">Complaint_ID, Category, Department, Date_Received, Status, Deadline, Resolution_Date, Assigned_Team, Priority, Delay_Reason, Last_Updated_Date</code>) as well as public municipal 311 CSVs.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">
                  <ShieldCheck className="w-3.5 h-3.5" /> Automatic Citizen PII Firewall
                </span>
                {sourceName && (
                  <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1 rounded-full font-medium">
                    <FileSpreadsheet className="w-3.5 h-3.5" /> Active: {sourceName}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Synthetic Generator */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-indigo-600" />
              <h3 className="text-sm font-semibold text-slate-900">Synthetic Public Complaint Generator</h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Load anonymized demonstration complaints with realistic deadlines, overdue backlogs, recorded delay reasons, and volume spikes.
            </p>
            <div className="mt-3 space-y-2.5 text-xs">
              <label className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                <span className="font-medium text-slate-700">Complaint Rows</span>
                <select
                  value={rowsCount}
                  onChange={(e) => setRowsCount(Number(e.target.value))}
                  className="bg-white border border-slate-300 rounded px-2 py-1 font-medium"
                >
                  <option value={300}>300 rows</option>
                  <option value={620}>620 rows</option>
                  <option value={1000}>1,000 rows</option>
                </select>
              </label>

              <label className="flex items-center gap-2 text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={injectPii}
                  onChange={(e) => setInjectPii(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600"
                />
                <span>Include simulated PII columns to test Zero-PII scrubbing</span>
              </label>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <a
              href={getSampleCsvDownloadUrl(rowsCount, injectPii)}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 px-3 py-2 rounded-lg"
            >
              <Download className="w-3.5 h-3.5" /> Download CSV
            </a>
            <button
              type="button"
              disabled={loading}
              onClick={() => onLoadSample({ numRows: rowsCount, includeSimulatedPii: injectPii })}
              className="flex-1 inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 px-4 py-2 rounded-lg"
            >
              {loading ? 'Processing...' : 'Generate & Analyze Dataset'}
            </button>
          </div>
        </div>
      </div>

      {/* PII Shield Audit & Column Auto-Mapping */}
      {piiReceipt && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <h3 className="text-sm font-semibold text-slate-900">
                Zero-PII Ingestion Audit &amp; Schema Mapping Receipt
              </h3>
            </div>
            <span className="text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full">
              {piiReceipt.shield_status} · {piiReceipt.input_rows} Rows · {piiReceipt.post_shield_leaks} Leaks
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 space-y-2">
              <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Mapped Operational Columns ({Object.keys(piiReceipt.mapped_columns || {}).length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(piiReceipt.mapped_columns || {}).map(([src, dst]) => (
                  <span key={src} className="bg-white border border-slate-200 rounded px-2 py-0.5 font-mono text-[11px]">
                    {src} → <strong className="text-blue-700">{dst}</strong>
                  </span>
                ))}
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 space-y-2">
              <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                <Trash2 className="w-4 h-4 text-rose-600" />
                Dropped PII / Non-Operational Columns ({piiReceipt.dropped_pii_columns?.length || 0})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {piiReceipt.dropped_pii_columns?.length ? (
                  piiReceipt.dropped_pii_columns.map((c) => (
                    <span key={c} className="bg-rose-50 text-rose-700 border border-rose-200 rounded px-2 py-0.5 font-mono text-[11px]">
                      {c}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-500">No PII or unmapped columns present in uploaded file.</span>
                )}
              </div>
              <div className="text-[11px] text-slate-500">
                Inline PII scrubbed: <strong>{piiReceipt.total_inline_pii_scrubbed}</strong> · Teams anonymized: <strong>{piiReceipt.teams_anonymized_count}</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sanitized Preview */}
      {previewRows.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">
            Sanitized Dataset Preview (First {previewRows.length} Anonymized Records)
          </h3>
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="py-2 px-3">Complaint ID</th>
                  <th className="py-2 px-3">Category</th>
                  <th className="py-2 px-3">Department</th>
                  <th className="py-2 px-3">Received</th>
                  <th className="py-2 px-3">Deadline</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Priority</th>
                  <th className="py-2 px-3">Team</th>
                  <th className="py-2 px-3">Delay Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {previewRows.map((r) => (
                  <tr key={r.Complaint_ID} className="hover:bg-slate-50">
                    <td className="py-2 px-3 font-mono font-semibold">{r.Complaint_ID}</td>
                    <td className="py-2 px-3">{r.Category}</td>
                    <td className="py-2 px-3">{r.Department}</td>
                    <td className="py-2 px-3 tabular-nums">{r.Date_Received}</td>
                    <td className="py-2 px-3 tabular-nums">{r.Deadline}</td>
                    <td className="py-2 px-3 font-medium">{r.Status}</td>
                    <td className="py-2 px-3">{r.Priority}</td>
                    <td className="py-2 px-3 font-mono">{r.Assigned_Team}</td>
                    <td className="py-2 px-3 text-slate-600">{r.Delay_Reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

