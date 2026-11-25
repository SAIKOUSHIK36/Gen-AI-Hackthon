import React from 'react'
import { X, ShieldCheck, Trash2, CheckCircle2, Lock } from 'lucide-react'

export default function PrivacyShieldModal({ open, piiAudit, onClose }) {
  if (!open || !piiAudit) return null

  const inlineBreakdown = Object.entries(piiAudit.scrubbed_inline_pii || {})

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden">
        <div className="px-5 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="text-sm font-semibold">Layer 2 Zero-Trust PII Shield Audit Receipt</h3>
              <p className="text-[11px] text-slate-300">
                Cryptographic &amp; structural proof that zero citizen PII enters Layer 3 or Layer 4
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-300 hover:text-white p-1 rounded-lg"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4 max-h-[80vh] overflow-y-auto text-xs">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
              <div className="text-slate-500">Rows Audited</div>
              <div className="text-lg font-bold text-slate-900 tabular-nums">{piiAudit.input_rows}</div>
            </div>
            <div className="bg-rose-50 border border-rose-200 rounded-lg p-3">
              <div className="text-rose-700">Dropped PII Columns</div>
              <div className="text-lg font-bold text-rose-800 tabular-nums">
                {piiAudit.dropped_pii_columns?.length ?? 0}
              </div>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="text-amber-700">Inline PII Scrubbed</div>
              <div className="text-lg font-bold text-amber-800 tabular-nums">
                {piiAudit.total_inline_pii_scrubbed ?? 0}
              </div>
            </div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
              <div className="text-emerald-700">Post-Shield Leaks</div>
              <div className="text-lg font-bold text-emerald-800 tabular-nums">
                {piiAudit.post_shield_pii_leaks_detected ?? 0}
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="font-semibold text-slate-800 flex items-center gap-1.5">
              <Trash2 className="w-4 h-4 text-rose-600" />
              Blocked &amp; Dropped Citizen PII / Free-Text Columns
            </div>
            <div className="flex flex-wrap gap-1.5 bg-slate-50 border border-slate-200 rounded-lg p-3">
              {piiAudit.dropped_pii_columns?.length ? (
                piiAudit.dropped_pii_columns.map((col) => (
                  <span
                    key={col}
                    className="font-mono bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded"
                  >
                    {col}
                  </span>
                ))
              ) : (
                <span className="text-slate-500">No forbidden PII columns present in source schema.</span>
              )}
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="font-semibold text-slate-800 flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-amber-600" />
              Inline Regex PII Scrubbing Breakdown (Operational Fields)
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {inlineBreakdown.map(([kind, count]) => (
                <div
                  key={kind}
                  className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
                >
                  <span className="capitalize text-slate-600">{kind.replace('_', ' ')}</span>
                  <span className="font-bold tabular-nums text-slate-900">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="font-semibold text-slate-800 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Strict Allowlisted Operational Schema Passed to Layer 3
            </div>
            <div className="flex flex-wrap gap-1.5 bg-emerald-50/50 border border-emerald-200 rounded-lg p-3">
              {(piiAudit.retained_safe_columns || []).map((col) => (
                <span
                  key={col}
                  className="font-mono bg-white text-emerald-800 border border-emerald-200 px-2 py-0.5 rounded"
                >
                  {col}
                </span>
              ))}
            </div>
            <p className="text-[11px] text-slate-500">
              Non-standard worker identifiers hashed via SHA-256 anonymizer: <strong>{piiAudit.worker_ids_anonymized_count ?? 0}</strong> records normalized to DEPT-NNN format.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
