import React, { useEffect, useState } from 'react'
import { Building2, ShieldCheck, AlertCircle } from 'lucide-react'
import {
  fetchHealth,
  loadSampleDataset,
  uploadServiceDataset,
  filterDataset,
  generateNarrative,
  exportExecutivePdf,
} from './api'
import ArchitectureBanner from './components/ArchitectureBanner'
import DataUploadBar from './components/DataUploadBar'
import KpiCards from './components/KpiCards'
import WorkloadCharts from './components/WorkloadCharts'
import WorkerAuditTable from './components/WorkerAuditTable'
import AiNarrativePanel from './components/AiNarrativePanel'
import PrivacyShieldModal from './components/PrivacyShieldModal'

export default function App() {
  const [sessionId, setSessionId] = useState(null)
  const [sourceLabel, setSourceLabel] = useState('')
  const [piiAudit, setPiiAudit] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [narrativeResult, setNarrativeResult] = useState(null)
  const [geminiConfigured, setGeminiConfigured] = useState(false)

  const [filters, setFilters] = useState({
    granularity: 'week',
    serviceCategory: 'All',
    status: 'All',
    priority: 'All',
  })

  const [loadingData, setLoadingData] = useState(false)
  const [generatingNarrative, setGeneratingNarrative] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [auditModalOpen, setAuditModalOpen] = useState(false)

  const handleLoadSample = async ({ numRows = 640, includeSimulatedPii = true } = {}) => {
    setLoadingData(true)
    setErrorMsg('')
    try {
      const res = await loadSampleDataset({
        numRows,
        includeSimulatedPii,
        granularity: filters.granularity,
      })
      setSessionId(res.session_id)
      setSourceLabel(res.source_label)
      setPiiAudit(res.pii_audit)
      setAnalytics(res.analytics)
      setGeminiConfigured(Boolean(res.gemini_configured))
      setFilters((f) => ({ ...f, serviceCategory: 'All', status: 'All', priority: 'All' }))
      setNarrativeResult(null)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load synthetic municipal dataset.')
    } finally {
      setLoadingData(false)
    }
  }

  useEffect(() => {
    fetchHealth()
      .then((h) => setGeminiConfigured(Boolean(h?.gemini_configured)))
      .catch(() => {})
    handleLoadSample({ numRows: 640, includeSimulatedPii: true })
  }, [])

  const handleUploadFile = async (file) => {
    setLoadingData(true)
    setErrorMsg('')
    try {
      const res = await uploadServiceDataset(file, filters.granularity)
      setSessionId(res.session_id)
      setSourceLabel(res.source_label)
      setPiiAudit(res.pii_audit)
      setAnalytics(res.analytics)
      setGeminiConfigured(Boolean(res.gemini_configured))
      setFilters((f) => ({ ...f, serviceCategory: 'All', status: 'All', priority: 'All' }))
      setNarrativeResult(null)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to process uploaded file.')
    } finally {
      setLoadingData(false)
    }
  }

  const handleFilterChange = async (nextFilters) => {
    setFilters(nextFilters)
    if (!sessionId) return
    setLoadingData(true)
    setErrorMsg('')
    try {
      const res = await filterDataset({
        sessionId,
        granularity: nextFilters.granularity,
        serviceCategory: nextFilters.serviceCategory,
        status: nextFilters.status,
        priority: nextFilters.priority,
      })
      setAnalytics(res.analytics)
      setNarrativeResult(null)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to apply filters.')
    } finally {
      setLoadingData(false)
    }
  }

  const handleGenerateNarrative = async ({ focusArea, apiKey, model }) => {
    if (!sessionId) return
    setGeneratingNarrative(true)
    setErrorMsg('')
    try {
      const res = await generateNarrative({
        sessionId,
        granularity: filters.granularity,
        serviceCategory: filters.serviceCategory,
        status: filters.status,
        priority: filters.priority,
        focusArea,
        apiKey,
        model,
      })
      setNarrativeResult(res.narrative_result)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to generate Layer 4 executive briefing.')
    } finally {
      setGeneratingNarrative(false)
    }
  }

  const handleExportPdf = async () => {
    if (!sessionId || !narrativeResult) return
    setExportingPdf(true)
    setErrorMsg('')
    try {
      const blob = await exportExecutivePdf({
        sessionId,
        granularity: filters.granularity,
        serviceCategory: filters.serviceCategory,
        status: filters.status,
        priority: filters.priority,
        narrativeResult,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'ps158_executive_workload_report.pdf'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to export executive PDF.')
    } finally {
      setExportingPdf(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Top Civic Header */}
      <header className="bg-slate-900 text-white border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-400/30 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-blue-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight">
                  PS 158: Public Service Workload Narrative Assistant
                </h1>
              </div>
              <p className="text-xs text-slate-300">
                Municipal Workload Analytics, Worker Accountability Audit &amp; Zero-PII GenAI Briefing System
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-400/30 px-3 py-1.5 rounded-full">
              <ShieldCheck className="w-4 h-4" />
              Zero Citizen PII Enforced
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-5 space-y-5">
        <ArchitectureBanner
          piiAudit={piiAudit}
          analyticsReady={Boolean(analytics && !analytics.empty)}
          narrativeReady={Boolean(narrativeResult)}
          onOpenAudit={() => setAuditModalOpen(true)}
        />

        {errorMsg && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl px-4 py-3 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <DataUploadBar
          loading={loadingData}
          sourceLabel={sourceLabel}
          availableFilters={analytics?.available_filters}
          filters={filters}
          onFilterChange={handleFilterChange}
          onLoadSample={handleLoadSample}
          onUploadFile={handleUploadFile}
        />

        {analytics && !analytics.empty ? (
          <>
            <KpiCards
              kpis={analytics.kpis}
              piiAudit={piiAudit}
              onOpenAudit={() => setAuditModalOpen(true)}
            />
            <WorkloadCharts analytics={analytics} />
            <AiNarrativePanel
              narrativeResult={narrativeResult}
              generating={generatingNarrative}
              exportingPdf={exportingPdf}
              geminiServerConfigured={geminiConfigured}
              onGenerate={handleGenerateNarrative}
              onExportPdf={handleExportPdf}
            />
            <WorkerAuditTable workers={analytics.worker_audit} />
          </>
        ) : analytics?.empty ? (
          <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-slate-500">
            No records match the active slice filters. Adjust or reset filters above.
          </div>
        ) : null}
      </main>

      <PrivacyShieldModal
        open={auditModalOpen}
        piiAudit={piiAudit}
        onClose={() => setAuditModalOpen(false)}
      />
    </div>
  )
}

