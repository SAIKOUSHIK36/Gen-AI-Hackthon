import React, { useRef, useState } from 'react'
import { Upload, Database, Download, Filter, RefreshCw } from 'lucide-react'
import { getSampleCsvUrl } from '../api'

export default function DataUploadBar({
  loading,
  sourceLabel,
  availableFilters,
  filters,
  onFilterChange,
  onLoadSample,
  onUploadFile,
}) {
  const fileInputRef = useRef(null)
  const [dragActive, setDragActive] = useState(false)
  const [sampleRows, setSampleRows] = useState(640)
  const [injectPii, setInjectPii] = useState(true)

  const handleFiles = (files) => {
    const file = files?.[0]
    if (file) {
      onUploadFile(file)
    }
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
        {/* Dropzone Upload */}
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
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
          }}
          className={`lg:col-span-6 border-2 border-dashed rounded-xl px-4 py-3.5 cursor-pointer transition-colors flex items-center gap-3.5 ${
            dragActive
              ? 'border-blue-500 bg-blue-50/60'
              : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50/80'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json"
            className="hidden"
            onChange={(e) => {
              handleFiles(e.target.files)
              e.target.value = ''
            }}
          />
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <Upload className="w-5 h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold text-slate-800">
              Upload Municipal Request Log (.CSV or .JSON)
            </div>
            <div className="text-xs text-slate-500 truncate">
              Layer 2 PII Shield immediately drops citizen names, phones, emails, addresses &amp; free-text before analysis.
            </div>
            {sourceLabel && (
              <div className="mt-1 inline-flex items-center gap-1.5 text-[11px] font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                Active Source: {sourceLabel}
              </div>
            )}
          </div>
        </div>

        {/* Synthetic Sample Controls */}
        <div className="lg:col-span-6 bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-slate-600" />
              <span className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
                Synthetic Demo Generator
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
              <label className="flex items-center gap-1.5">
                Rows:
                <select
                  value={sampleRows}
                  onChange={(e) => setSampleRows(Number(e.target.value))}
                  className="bg-white border border-slate-300 rounded px-2 py-1 text-xs font-medium text-slate-800"
                >
                  <option value={520}>520 rows</option>
                  <option value={640}>640 rows</option>
                  <option value={900}>900 rows</option>
                  <option value={1200}>1,200 rows</option>
                </select>
              </label>
              <label className="inline-flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={injectPii}
                  onChange={(e) => setInjectPii(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span>Include test citizen PII (stress-test Layer 2)</span>
              </label>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <a
              href={getSampleCsvUrl(sampleRows)}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 px-3 py-2 rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Sample CSV
            </a>
            <button
              type="button"
              disabled={loading}
              onClick={() => onLoadSample({ numRows: sampleRows, includeSimulatedPii: injectPii })}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 px-3.5 py-2 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Load Demo Dataset
            </button>
          </div>
        </div>
      </div>

      {/* Slice Filters */}
      {availableFilters && (
        <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide mr-1">
            <Filter className="w-3.5 h-3.5" />
            Slice View:
          </div>

          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
            {['week', 'month'].map((gran) => (
              <button
                key={gran}
                type="button"
                onClick={() => onFilterChange({ ...filters, granularity: gran })}
                className={`px-2.5 py-1 text-xs font-medium rounded-md capitalize transition-colors ${
                  filters.granularity === gran
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {gran}ly
              </button>
            ))}
          </div>

          <select
            aria-label="Filter by Service Category"
            value={filters.serviceCategory}
            onChange={(e) => onFilterChange({ ...filters, serviceCategory: e.target.value })}
            className="text-xs font-medium bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700"
          >
            <option value="All">All Service Categories</option>
            {availableFilters.categories?.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by Status"
            value={filters.status}
            onChange={(e) => onFilterChange({ ...filters, status: e.target.value })}
            className="text-xs font-medium bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700"
          >
            <option value="All">All Statuses</option>
            {availableFilters.statuses?.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by Priority"
            value={filters.priority}
            onChange={(e) => onFilterChange({ ...filters, priority: e.target.value })}
            className="text-xs font-medium bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700"
          >
            <option value="All">All Priorities</option>
            {availableFilters.priorities?.map((pr) => (
              <option key={pr} value={pr}>
                {pr}
              </option>
            ))}
          </select>

          {(filters.serviceCategory !== 'All' || filters.status !== 'All' || filters.priority !== 'All') && (
            <button
              type="button"
              onClick={() =>
                onFilterChange({
                  ...filters,
                  serviceCategory: 'All',
                  status: 'All',
                  priority: 'All',
                })
              }
              className="text-xs font-medium text-blue-600 hover:text-blue-800 px-2 py-1"
            >
              Reset filters
            </button>
          )}
        </div>
      )}
    </section>
  )
}

