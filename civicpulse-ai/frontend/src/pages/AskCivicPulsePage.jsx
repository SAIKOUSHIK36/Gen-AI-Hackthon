import React, { useState } from 'react'
import { MessageSquare, Send, Sparkles, ShieldCheck } from 'lucide-react'

const SUGGESTED_QUESTIONS = [
  'How many complaints are resolved?',
  'How many complaints are pending?',
  'Why are complaints getting delayed?',
  'Which department has the most overdue complaints?',
  'What is the main recorded reason for delays?',
  'Which department is performing poorly?',
  'Which complaints need immediate attention?',
  'How can we reduce the pending workload?',
]

export default function AskCivicPulsePage({ chatHistory = [], asking, onAsk }) {
  const [input, setInput] = useState('')

  const submitQuestion = (q) => {
    const trimmed = (q ?? input).trim()
    if (!trimmed || asking) return
    onAsk(trimmed)
    if (q === undefined) setInput('')
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* Suggested Questions Sidebar */}
      <div className="lg:col-span-4 bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3 h-fit">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-slate-900">Administrator Quick Prompts</h3>
        </div>
        <p className="text-xs text-slate-500">
          Ask CivicPulse AI answers strictly from Python-computed statistics and uploaded evidence — zero invented figures.
        </p>
        <div className="space-y-1.5">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              disabled={asking}
              onClick={() => submitQuestion(q)}
              className="w-full text-left text-xs font-medium text-slate-700 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 hover:border-blue-200 rounded-lg px-3 py-2 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Conversation */}
      <div className="lg:col-span-8 bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col h-[600px]">
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-slate-900">Ask CivicPulse AI</h3>
          </div>
          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full font-medium">
            <ShieldCheck className="w-3.5 h-3.5" /> Grounded in Dataset Statistics
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
          {chatHistory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-xs text-slate-500 max-w-md mx-auto">
              <Sparkles className="w-8 h-8 text-blue-400 mb-2" />
              <div className="font-semibold text-slate-700 mb-1">Ready for Administrative Q&amp;A</div>
              <p>
                Select any prompt on the left or ask your own question about complaint resolution rates, overdue backlogs, or department bottlenecks.
              </p>
            </div>
          ) : (
            chatHistory.map((turn, idx) => (
              <div
                key={idx}
                className={`flex ${turn.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed whitespace-pre-line ${
                    turn.role === 'user'
                      ? 'bg-slate-900 text-white rounded-br-sm'
                      : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm'
                  }`}
                >
                  {turn.message}
                  {turn.role === 'assistant' && turn.engine_mode && (
                    <div className="mt-1.5 text-[10px] text-slate-400">
                      Source: {turn.engine_mode === 'gemini_live' ? 'Google Gemini (Grounded)' : 'Deterministic Analytics Engine'}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {asking && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-2xl px-4 py-2.5 text-xs text-slate-500">
                Analyzing dataset statistics...
              </div>
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            submitQuestion()
          }}
          className="p-3 border-t border-slate-200 bg-white flex items-center gap-2 rounded-b-xl"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about resolved counts, overdue departments, delay reasons, or recommendations..."
            className="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={asking || !input.trim()}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg"
          >
            <Send className="w-3.5 h-3.5" /> Ask
          </button>
        </form>
      </div>
    </div>
  )
}
