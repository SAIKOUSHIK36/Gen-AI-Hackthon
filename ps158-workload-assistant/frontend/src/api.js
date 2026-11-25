const API_BASE = import.meta.env.VITE_API_BASE || '';

async function handleResponse(res) {
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    try {
      const payload = await res.json();
      if (payload?.detail) message = payload.detail;
    } catch {
      // keep fallback message
    }
    throw new Error(message);
  }
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  return handleResponse(res);
}

export async function loadSampleDataset({ numRows = 640, includeSimulatedPii = true, granularity = 'week' } = {}) {
  const res = await fetch(`${API_BASE}/api/analyze/sample`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      num_rows: numRows,
      include_simulated_pii: includeSimulatedPii,
      granularity,
    }),
  });
  return handleResponse(res);
}

export async function uploadServiceDataset(file, granularity = 'week') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('granularity', granularity);
  const res = await fetch(`${API_BASE}/api/analyze/upload`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse(res);
}

export async function filterDataset({ sessionId, granularity, serviceCategory, status, priority }) {
  const res = await fetch(`${API_BASE}/api/filter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      granularity,
      service_category: serviceCategory === 'All' ? null : serviceCategory,
      status: status === 'All' ? null : status,
      priority: priority === 'All' ? null : priority,
    }),
  });
  return handleResponse(res);
}

export async function generateNarrative({
  sessionId,
  granularity,
  serviceCategory,
  status,
  priority,
  focusArea,
  apiKey,
  model,
}) {
  const res = await fetch(`${API_BASE}/api/narrative`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      granularity,
      service_category: serviceCategory === 'All' ? null : serviceCategory,
      status: status === 'All' ? null : status,
      priority: priority === 'All' ? null : priority,
      focus_area: focusArea || '',
      api_key: apiKey || null,
      model: model || null,
    }),
  });
  return handleResponse(res);
}

export async function exportExecutivePdf({
  sessionId,
  granularity,
  serviceCategory,
  status,
  priority,
  narrativeResult,
}) {
  const res = await fetch(`${API_BASE}/api/export/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      granularity,
      service_category: serviceCategory === 'All' ? null : serviceCategory,
      status: status === 'All' ? null : status,
      priority: priority === 'All' ? null : priority,
      narrative_result: narrativeResult,
    }),
  });
  if (!res.ok) {
    throw new Error(`PDF export failed (${res.status})`);
  }
  return res.blob();
}

export function getSampleCsvUrl(rows = 640) {
  return `${API_BASE}/api/sample-data/csv?rows=${rows}&include_pii=true`;
}

