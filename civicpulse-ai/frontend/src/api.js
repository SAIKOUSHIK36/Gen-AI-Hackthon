import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 60000,
})

function extractError(err) {
  return err?.response?.data?.detail || err?.message || 'Unexpected API error'
}

export async function fetchHealth() {
  try {
    const { data } = await api.get('/api/health')
    return data
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function loadSampleDataset({ numRows = 620, includeSimulatedPii = false, granularity = 'week' } = {}) {
  try {
    const { data } = await api.post('/api/datasets/sample', {
      num_rows: numRows,
      include_simulated_pii: includeSimulatedPii,
      granularity,
    })
    return data
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function uploadComplaintFile(file, granularity = 'week') {
  try {
    const form = new FormData()
    form.append('file', file)
    form.append('granularity', granularity)
    const { data } = await api.post('/api/datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function applyAnalyticsFilters({ sessionId, department, category, status, priority, granularity }) {
  try {
    const { data } = await api.post('/api/analytics/filter', {
      session_id: sessionId,
      department: department === 'All' ? null : department,
      category: category === 'All' ? null : category,
      status: status === 'All' ? null : status,
      priority: priority === 'All' ? null : priority,
      granularity,
    })
    return data
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function generateAdminReport({
  sessionId,
  title,
  focusPrompt,
  department,
  category,
  status,
  priority,
  granularity,
  apiKey,
  model,
}) {
  try {
    const { data } = await api.post('/api/reports/generate', {
      session_id: sessionId,
      title,
      focus_prompt: focusPrompt || '',
      department: department === 'All' ? null : department,
      category: category === 'All' ? null : category,
      status: status === 'All' ? null : status,
      priority: priority === 'All' ? null : priority,
      granularity,
      api_key: apiKey || null,
      model: model || null,
    })
    return data
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function fetchReportsHistory() {
  try {
    const { data } = await api.get('/api/reports')
    return data.reports || []
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function downloadReportPdf({ reportId, sessionId, reportBundle, filters }) {
  try {
    const res = await api.post(
      '/api/reports/pdf',
      reportId
        ? { report_id: reportId }
        : {
            session_id: sessionId,
            report_bundle: reportBundle,
            department: filters?.department === 'All' ? null : filters?.department,
            category: filters?.category === 'All' ? null : filters?.category,
            status: filters?.status === 'All' ? null : filters?.status,
            priority: filters?.priority === 'All' ? null : filters?.priority,
            granularity: filters?.granularity || 'week',
          },
      { responseType: 'blob' },
    )
    return res.data
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function askCivicPulse({ sessionId, question, filters, apiKey, model }) {
  try {
    const { data } = await api.post('/api/ask', {
      session_id: sessionId,
      question,
      department: filters?.department === 'All' ? null : filters?.department,
      category: filters?.category === 'All' ? null : filters?.category,
      status: filters?.status === 'All' ? null : filters?.status,
      priority: filters?.priority === 'All' ? null : filters?.priority,
      granularity: filters?.granularity || 'week',
      api_key: apiKey || null,
      model: model || null,
    })
    return data
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function fetchChatHistory(sessionId) {
  try {
    const { data } = await api.get(`/api/ask/history/${sessionId}`)
    return data.history || []
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export async function fetchAuditLogs(limit = 100) {
  try {
    const { data } = await api.get(`/api/audit-logs?limit=${limit}`)
    return data.logs || []
  } catch (err) {
    throw new Error(extractError(err))
  }
}

export function getSampleCsvDownloadUrl(rows = 620, includePii = false) {
  return `${import.meta.env.VITE_API_BASE || ''}/api/sample-data/csv?rows=${rows}&include_pii=${includePii}`
}

