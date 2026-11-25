import React, { useEffect, useState } from 'react'
import {
  LayoutDashboard,
  UploadCloud,
  PieChart as PieIcon,
  ClockAlert,
  Building2,
  MessageSquare,
  FileText,
  ScrollText,
  ShieldCheck,
  KeyRound,
  AlertCircle,
  Filter,
} from 'lucide-react'
import {
  fetchHealth,
  loadSampleDataset,
  uploadComplaintFile,
  applyAnalyticsFilters,
  generateAdminReport,
  fetchReportsHistory,
  downloadReportPdf,
  askCivicPulse,
  fetchAuditLogs,
} from './api'
import DashboardPage from './pages/DashboardPage'
import UploadDatasetPage from './pages/UploadDatasetPage'
import ResolutionAnalysisPage from './pages/ResolutionAnalysisPage'
import DelayAnalysisPage from './pages/DelayAnalysisPage'
import DepartmentPerformancePage from './pages/DepartmentPerformancePage'
import AskCivicPulsePage from './pages/AskCivicPulsePage'
import ReportsPage from './pages/ReportsPage'
import AuditLogsPage from './pages/AuditLogsPage'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'upload', label: 'Upload Complaint Dataset', icon: UploadCloud },
  { id: 'resolution', label: 'Complaint Resolution Analysis', icon: PieIcon },
  { id: 'delays', label: 'Delay Reason Analysis', icon: ClockAlert },
  { id: 'departments', label: 'Department Performance', icon: Building2 },
  { id: 'ask', label: 'Ask CivicPulse AI', icon: MessageSquare },
  { id: 'reports', label: 'AI Administrative Reports', icon: FileText },
  { id: 'audit', label: 'Audit Logs', icon: ScrollText },
]

export default function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [sessionId, setSessionId] = useState(null)
  const [sourceName, setSourceName] = useState('')
  const [piiReceipt, setPiiReceipt] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [previewRows, setPreviewRows] = useState([])

  const [filters, setFilters] = useState({
    department: 'All',
    category: 'All',
    status: 'All',
    priority: 'All',
    granularity: 'week',
  })

  const [chatHistory, setChatHistory] = useState([])
  const [activeReport, setActiveReport] = useState(null)
  const [savedReports, setSavedReports] = useState([])
  const [auditLogs, setAuditLogs] = useState([])

  const [geminiConfigured, setGeminiConfigured] = useState(false)
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [modelName, setModelName] = useState('gemini-2.5-flash')

  const [loadingData, setLoadingData] = useState(false)
  const [asking, setAsking] = useState(false)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const refreshHistoryAndLogs = async () => {
    try {
      const [rpts, logs] = await Promise.all([fetchReportsHistory(), fetchAuditLogs()])
      setSavedReports(rpts)
      setAuditLogs(logs)
    } catch {
      // non-blocking
    }
  }

  const handleLoadSample = async ({ numRows = 620, includeSimulatedPii = false } = {}) => {
    setLoadingData(true)
    setErrorMsg('')
    try {
      const res = await loadSampleDataset({
        numRows,
        includeSimulatedPii,
        granularity: filters.granularity,
      })
      setSessionId(res.session_id)
      setSourceName(res.source_name)
      setPiiReceipt(res.pii_receipt)
      setAnalytics(res.analytics)
      setPreviewRows(res.preview_rows || [])
      setGeminiConfigured(Boolean(res.gemini_configured))
      setChatHistory([])
      setActiveReport(null)
      setFilters((f) => ({ ...f, department: 'All', category: 'All', status: 'All', priority: 'All' }))
      await refreshHistoryAndLogs()
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setLoadingData(false)
    }
  }

  useEffect(() => {
    fetchHealth()
      .then((h) => setGeminiConfigured(Boolean(h?.gemini_configured)))
      .catch(() => {})
    handleLoadSample({ numRows: 620, includeSimulatedPii: false })
  }, [])

  const handleUploadFile = async (file) => {
    setLoadingData(true)
    setErrorMsg('')
    try {
      const res = await uploadComplaintFile(file, filters.granularity)
      setSessionId(res.session_id)
      setSourceName(res.source_name)
      setPiiReceipt(res.pii_receipt)
      setAnalytics(res.analytics)
      setPreviewRows(res.preview_rows || [])
      setChatHistory([])
      setActiveReport(null)
      setFilters((f) => ({ ...f, department: 'All', category: 'All', status: 'All', priority: 'All' }))
      await refreshHistoryAndLogs()
    } catch (err) {
      setErrorMsg(err.message)
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
      const res = await applyAnalyticsFilters({ sessionId, ...nextFilters })
      setAnalytics(res.analytics)
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setLoadingData(false)
    }
  }

  const handleAsk = async (question) => {
    if (!sessionId) return
    setAsking(true)
    setErrorMsg('')
    try {
      const res = await askCivicPulse({
        sessionId,
        question,
        filters,
        apiKey,
        model: modelName,
      })
      setChatHistory(res.history || [])
      await refreshHistoryAndLogs()
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setAsking(false)
    }
  }

  const handleGenerateReport = async ({ title, focusPrompt }) => {
    if (!sessionId) return
    setGeneratingReport(true)
    setErrorMsg('')
    try {
      const res = await generateAdminReport({
        sessionId,
        title,
        focusPrompt,
        ...filters,
        apiKey,
        model: modelName,
      })
      setActiveReport({
        report_id: res.report_id,
        title,
        report_bundle: res.report_bundle,
      })
      await refreshHistoryAndLogs()
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setGeneratingReport(false)
    }
  }

  const handleDownloadPdf = async ({ reportId, reportBundle }) => {
    setExportingPdf(true)
    setErrorMsg('')
    try {
      const blob = await downloadReportPdf({ reportId, sessionId, reportBundle, filters })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${reportId || 'civicpulse_report'}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      await refreshHistoryAndLogs()
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setExportingPdf(false)
    }
  }

  const handleSelectSavedReport = (saved) => {
    setActiveReport({
      report_id: saved.report_id,
      title: saved.title,
      report_bundle: saved.report_data,
    })
  }

  const avail = analytics?.available_filters

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50 text-slate-900">
      {/* Persistent Navigation Sidebar (8 Required Pages) */}
      <aside className="lg:w-64 bg-slate-900 text-slate-100 flex flex-col shrink-0 border-r border-slate-800">
        <div className="p-4 border-b border-slate-800">
          <div className="text-lg font-bold tracking-tight text-white">CivicPulse AI</div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Complaint Resolution &amp; Delay Intelligence
          </p>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-x-auto lg:overflow-visible flex lg:flex-col gap-1 lg:gap-0">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const active = activePage === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setActivePage(item.id)
                  if (item.id === 'reports' || item.id === 'audit') refreshHistoryAndLogs()
                }}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors whitespace-nowrap lg:w-full text-left ${
                  active
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="p-3 border-t border-slate-800 space-y-2 text-[11px]">
          <div className="flex items-center gap-1.5 text-emerald-300 font-medium">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>Zero Citizen PII Enforced</span>
          </div>
          <button
            type="button"
            onClick={() => setShowKeyModal((v) => !v)}
            className="w-full flex items-center justify-between bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-lg transition-colors"
          >
            <span className="inline-flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5" />
              Gemini API Settings
            </span>
            <span className={`w-2 h-2 rounded-full ${geminiConfigured || apiKey ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Filter & Context Bar */}
        <header className="bg-white border-b border-slate-200 px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-base font-bold text-slate-900">
              {NAV_ITEMS.find((n) => n.id === activePage)?.label}
            </h1>
            <p className="text-xs text-slate-500">
              {sourceName ? `Active Dataset: ${sourceName}` : 'Loading complaint analytics...'}
            </p>
          </div>

          {avail && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={filters.department}
                onChange={(e) => handleFilterChange({ ...filters, department: e.target.value })}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white font-medium"
              >
                <option value="All">All Departments</option>
                {avail.departments?.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>

              <select
                value={filters.status}
                onChange={(e) => handleFilterChange({ ...filters, status: e.target.value })}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white font-medium"
              >
                <option value="All">All Statuses</option>
                {avail.statuses?.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>

              <select
                value={filters.priority}
                onChange={(e) => handleFilterChange({ ...filters, priority: e.target.value })}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white font-medium"
              >
                <option value="All">All Priorities</option>
                {avail.priorities?.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>

              <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
                {['week', 'month'].map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => handleFilterChange({ ...filters, granularity: g })}
                    className={`px-2 py-1 rounded-md capitalize font-medium ${
                      filters.granularity === g ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
          )}
        </header>

        {showKeyModal && (
          <div className="bg-slate-100 border-b border-slate-200 px-6 py-3 flex flex-wrap items-center gap-3 text-xs">
            <span className="font-semibold text-slate-700">Google Gemini API Key (session memory only):</span>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={geminiConfigured ? 'Configured on backend .env' : 'AIza... (optional)'}
              className="border border-slate-300 rounded-lg px-3 py-1.5 bg-white w-64"
            />
            <select
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white"
            >
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              <option value="gemini-2.0-flash">gemini-2.0-flash</option>
            </select>
            <button
              type="button"
              onClick={() => setShowKeyModal(false)}
              className="bg-slate-900 text-white px-3 py-1.5 rounded-lg font-medium"
            >
              Done
            </button>
          </div>
        )}

        <main className="flex-1 p-4 sm:p-6 max-w-7xl w-full mx-auto space-y-4">
          {errorMsg && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl px-4 py-3 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {activePage === 'dashboard' && <DashboardPage analytics={analytics} onNavigate={setActivePage} />}
          {activePage === 'upload' && (
            <UploadDatasetPage
              loading={loadingData}
              sourceName={sourceName}
              piiReceipt={piiReceipt}
              previewRows={previewRows}
              onLoadSample={handleLoadSample}
              onUploadFile={handleUploadFile}
            />
          )}
          {activePage === 'resolution' && <ResolutionAnalysisPage analytics={analytics} />}
          {activePage === 'delays' && <DelayAnalysisPage analytics={analytics} />}
          {activePage === 'departments' && <DepartmentPerformancePage analytics={analytics} />}
          {activePage === 'ask' && (
            <AskCivicPulsePage chatHistory={chatHistory} asking={asking} onAsk={handleAsk} />
          )}
          {activePage === 'reports' && (
            <ReportsPage
              activeReport={activeReport}
              savedReports={savedReports}
              generating={generatingReport}
              exportingPdf={exportingPdf}
              onGenerateReport={handleGenerateReport}
              onDownloadPdf={handleDownloadPdf}
              onSelectSavedReport={handleSelectSavedReport}
            />
          )}
          {activePage === 'audit' && (
            <AuditLogsPage logs={auditLogs} onRefresh={refreshHistoryAndLogs} />
          )}
        </main>
      </div>
    </div>
  )
}
