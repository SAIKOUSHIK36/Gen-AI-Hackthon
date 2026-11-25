import React, { useState } from 'react'
import {
  Sparkles,
  FileDown,
  ShieldCheck,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Code2,
} from 'lucide-react'

export default function AiNarrativePanel({
  narrativeResult,
  generating,
  exportingPdf,
  geminiServerConfigured,
  onGenerate,
  onExportPdf,
}) {
  const [focusArea, setFocusArea] = useState('')
  const [showKeyConfig, setShowKeyConfig] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [modelName, setModelName] = useState('gemini-2.5-flash')
  const [showKeyText, setShowKeyText] = useState(false)
  const [showPayloadPreview, setShowPayloadPreview] = useState(false)

  const narrative = narrativeResult?.narrative
  const guardrails = narrativeResult?.guardrails
  const preflightOk = guardrails?.preflight?.preflight_passed
  const postOk = guardrails?.post_output?.output_pii_scan_passed
  const groundingOk = guardrails?.post_output?.worker_id_grounding_passed

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-violet-600" />
            <h2 className="text-base font-semibold text-slate-900">
              Layer 4: Executive Workload Narrative &amp; Guardrail Engine
            </h2>
            {narrativeResult && (
              <span
                className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  narrativeResult.mode === 'gemini_live'
                    ? 'bg-violet-50 text-violet-700 border-violet-200'
                    : 'bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                {narrativeResult.mode === 'gemini_live'
                  ? `Live Gemini (${narrativeResult.model})`
                  : 'Data-Grounded Deterministic Fallback'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Synthesizes executive briefing strictly from Layer 3 aggregated KPIs &amp; anonymized worker audit summaries. Zero raw rows or citizen PII ever leave Layer 2.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setShowKeyConfig((v) => !v)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-2 rounded-lg transition-colors"
          >
            <KeyRound className="w-3.5 h-3.5" />
            {geminiServerConfigured || apiKey ? 'Gemini Config' : 'Set Gemini Key (Optional)'}
          </button>

          <button
            type="button"
            disabled={generating}
            onClick={() => onGenerate({ focusArea, apiKey, model: modelName })}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50 px-4 py-2 rounded-lg transition-colors shadow-sm"
          >
            <Sparkles className={`w-3.5 h-3.5 ${generating ? 'animate-pulse' : ''}`} />
            {generating ? 'Synthesizing Briefing...' : narrative ? 'Regenerate Report' : 'Generate AI Executive Report'}
          </button>

          {narrative && (
            <button
              type="button"
              disabled={exportingPdf}
              onClick={onExportPdf}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 px-3.5 py-2 rounded-lg transition-colors"
            >
              <FileDown className="w-3.5 h-3.5" />
              {exportingPdf ? 'Building PDF...' : 'Export PDF'}
            </button>
          )}
        </div>
      </div>

      {/* Focus Area + Optional API Key Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        <div className={showKeyConfig ? 'lg:col-span-6' : 'lg:col-span-12'}>
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-1">
            Administrative Briefing Focus (Optional)
          </label>
          <input
            type="text"
            value={focusArea}
            onChange={(e) => setFocusArea(e.target.value)}
            placeholder="e.g., Audit overdue Roads & Water queues, highlight overloaded worker IDs, and recommend 30-day interventions"
            className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>

        {showKeyConfig && (
          <div className="lg:col-span-6 bg-slate-50 border border-slate-200 rounded-lg p-3 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Session Gemini API Key (memory only)
              </label>
              <div className="relative">
                <input
                  type={showKeyText ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={geminiServerConfigured ? 'Configured in backend .env' : 'AIza... (optional)'}
                  className="w-full pl-2.5 pr-8 py-1.5 text-xs bg-white border border-slate-300 rounded-md"
                />
                <button
                  type="button"
                  onClick={() => setShowKeyText((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showKeyText ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Gemini Model
              </label>
              <select
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-md"
              >
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                <option value="gemini-2.0-flash">gemini-2.0-flash</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Narrative Output */}
      {narrative ? (
        <div className="space-y-4 pt-2">
          {/* Guardrail Verification Strip */}
          <div className="flex flex-wrap items-center justify-between gap-2 bg-emerald-50/70 border border-emerald-200 rounded-lg px-3.5 py-2.5 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-800">
                <ShieldCheck className="w-4 h-4" />
                Layer 4 Guardrails:
              </span>
              <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                {preflightOk ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5 text-rose-600" />}
                Pre-Flight PII Firewall ({guardrails?.preflight?.payload_bytes ?? 0} bytes aggregated JSON)
              </span>
              <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                {postOk ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5 text-rose-600" />}
                Post-Output PII Scan (0 leaks)
              </span>
              <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                {groundingOk ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5 text-amber-600" />}
                Worker ID Grounding ({guardrails?.post_output?.cited_worker_ids?.length ?? 0} verified IDs)
              </span>
            </div>

            <button
              type="button"
              onClick={() => setShowPayloadPreview((v) => !v)}
              className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 hover:text-emerald-950 underline"
            >
              <Code2 className="w-3.5 h-3.5" />
              {showPayloadPreview ? 'Hide Sanitized LLM Input' : 'Inspect Sanitized LLM Input'}
            </button>
          </div>

          {narrative.generation_note && narrativeResult.mode !== 'gemini_live' && (
            <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
              <strong>Engine Note:</strong> {narrative.generation_note}
            </div>
          )}

          {showPayloadPreview && (
            <div className="bg-slate-900 text-slate-100 rounded-lg p-3.5 text-[11px] font-mono overflow-x-auto max-h-72 overflow-y-auto">
              <div className="text-emerald-400 font-semibold mb-1.5">
                // EXACT AGGREGATED ZERO-PII JSON PASSED TO LAYER 4
              </div>
              <pre>{JSON.stringify(narrativeResult.llm_payload_preview, null, 2)}</pre>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-blue-700">
                1. Executive Summary
              </h3>
              <p className="text-sm text-slate-800 leading-relaxed">{narrative.executive_summary}</p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-700">
                2. Time-Period Workload &amp; Backlog Trajectory
              </h3>
              <p className="text-sm text-slate-800 leading-relaxed">
                {narrative.workload_and_backlog_analysis}
              </p>
            </div>
          </div>

          {/* Bottlenecks */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
              3. Service Category Bottlenecks
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {(narrative.category_bottlenecks || []).map((b, i) => (
                <div key={i} className="border border-slate-200 rounded-xl p-3.5 bg-white space-y-1.5">
                  <div className="text-sm font-semibold text-slate-900">{b.category}</div>
                  <p className="text-xs text-slate-600">{b.evidence}</p>
                  <p className="text-xs text-slate-700">
                    <strong>Driver:</strong> {b.operational_driver}
                  </p>
                  <p className="text-xs text-blue-700 font-medium">
                    <strong>Action:</strong> {b.recommended_action}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Worker Accountability & Recommendations */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-5 bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-1.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-700">
                4. Anonymized Worker Accountability Audit
              </h3>
              <p className="text-sm text-slate-800 leading-relaxed">
                {narrative.worker_accountability_audit}
              </p>
            </div>

            <div className="lg:col-span-7 bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-violet-700">
                5. Administrative Recommendations
              </h3>
              <div className="space-y-2">
                {(narrative.administrative_recommendations || []).map((rec, i) => (
                  <div key={i} className="bg-white border border-slate-200 rounded-lg p-2.5 text-xs">
                    <span className="inline-block font-semibold text-violet-700 bg-violet-50 px-2 py-0.5 rounded mr-2">
                      {rec.priority}
                    </span>
                    <span className="text-slate-800 font-medium">{rec.action}</span>
                    {rec.expected_impact && (
                      <div className="text-slate-500 mt-1">Expected Impact: {rec.expected_impact}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-500 border-t border-slate-100 pt-2.5 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>{narrative.privacy_attestation}</span>
          </div>
        </div>
      ) : (
        <div className="bg-slate-50 border border-dashed border-slate-300 rounded-xl p-6 text-center text-xs text-slate-500">
          Click <strong>Generate AI Executive Report</strong> to run Layer 4 synthesis over the current sanitized metrics slice.
        </div>
      )}
    </section>
  )
}

