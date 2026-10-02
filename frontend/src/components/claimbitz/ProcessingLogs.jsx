import React, { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, ChevronDown, Loader2, Terminal } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * Parse a real log line into Lovable-style { level, agent, message } for
 * three-column presentation. The data itself is never fabricated — only
 * reformatted from the existing `[LEVEL] Agent: message` pattern.
 */
function parseLog(text) {
  // Match patterns like "[SUCCESS] Scanner Agent: Demo claim..." or "[SYSTEM] Connected to..."
  const m = text.match(/^\[(\w+)\]\s*(?:([^:]+?):\s*)?(.+)$/)
  if (!m) return { level: '', agent: '', message: text }
  const level = m[1] // SUCCESS, WARN, ERROR, DATA, SYSTEM, INFO, AGENT
  let agent = (m[2] || '').trim()
  let message = (m[3] || '').trim()
  // Some logs are "[SYSTEM] Pipeline: ..." or "[AGENT] Pipeline: ..."
  if (!agent && message) { agent = level === 'SYSTEM' ? 'System' : level; message = message }
  // Shorten long agent names for the fixed-width column
  if (agent.length > 12) agent = agent.split(' ')[0]
  return { level, agent, message }
}

function levelColor(level) {
  switch (level) {
    case 'SUCCESS': return 'text-[#4ADE80]'
    case 'WARN': return 'text-[#FBBF24]'
    case 'ERROR': return 'text-[#F87171]'
    case 'DATA': return 'text-[#E8965A]'
    default: return 'text-terminal-foreground/80'
  }
}

function rowStatusColor(status) {
  switch ((status || '').toLowerCase()) {
    case 'success': return 'text-[#4ADE80]'
    case 'warning': return 'text-[#FBBF24]'
    case 'error': return 'text-[#F87171]'
    default: return 'text-terminal-foreground/80'
  }
}

/**
 * Structured log rows from the backend `data.logs` (design §13.3). Each row
 * carries timestamp, agent (display name), action, input/output summary,
 * status, duration, confidence, error and requestId. Rendered inside the same
 * collapsible terminal styling as the free-text logs.
 */
function StructuredRows({ rows }) {
  return (
    <div className="space-y-1.5">
      {rows.map((r, i) => {
        const conf = typeof r.confidence === 'number' ? ` · conf ${Math.round(r.confidence * 100)}%` : ''
        const dur = r.duration_ms != null ? ` · ${r.duration_ms}ms` : ''
        const io = [r.input_summary, r.output_summary].filter(Boolean).join(' → ')
        return (
          <div key={i} className="border-b border-terminal-muted/20 pb-1.5 last:border-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
              <span className="w-40 shrink-0 truncate text-primary-border">{r.agent || r.agent_role || 'agent'}</span>
              <span className={rowStatusColor(r.status)}>{r.action || '—'}</span>
              <span className="text-terminal-muted">[{(r.status || 'info').toLowerCase()}{dur}{conf}]</span>
              {r.request_id && <span className="text-terminal-muted/70">req {String(r.request_id).slice(0, 8)}</span>}
            </div>
            {io && <p className="pl-40 text-terminal-foreground/70">{io}</p>}
            {r.error && <p className="pl-40 text-[#F87171]">error: {r.error}</p>}
          </div>
        )
      })}
    </div>
  )
}

/**
 * Processing logs — Lovable three-column visual, REAL data.
 * `logs` is the live terminalLogs array from useClaimAgent ({ text, timestamp }).
 * `structuredLogs` (optional) is the backend `data.logs` rows; when present a
 * structured per-agent view is shown above the terminal stream.
 * `state`: 'idle' | 'running' | 'complete' | 'failed'
 */
export function ProcessingLogs({ logs = [], structuredLogs = [], state = 'idle' }) {
  // Collapsed by default to match Lovable's console presentation.
  const [open, setOpen] = useState(false)
  const scrollRef = useRef(null)
  const rows = Array.isArray(structuredLogs) ? structuredLogs : []

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [logs])

  return (
    <section className="panel overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left transition-colors hover:bg-surface-muted"
        aria-expanded={open}
      >
        <span className="flex min-w-0 items-center gap-2.5">
          <Terminal className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="whitespace-nowrap text-[15px] font-semibold text-foreground">Processing logs</span>
          <span className="rounded bg-surface-muted px-1.5 py-0.5 text-xs font-medium tabular-nums text-muted-foreground">
            {logs.length}<span className="hidden sm:inline"> events</span>
          </span>
        </span>
        <span className="ml-auto mr-2 inline-flex items-center gap-1 text-xs font-medium">
          {state === 'complete' && (
            <span className="inline-flex items-center gap-1 text-success"><CheckCircle2 className="h-3.5 w-3.5" /> Complete</span>
          )}
          {state === 'running' && (
            <span className="inline-flex items-center gap-1 text-accent-foreground"><Loader2 className="h-3.5 w-3.5 motion-safe:animate-spin" /> Streaming</span>
          )}
          {state === 'failed' && (
            <span className="inline-flex items-center gap-1 text-destructive"><AlertTriangle className="h-3.5 w-3.5" /> Stopped</span>
          )}
          {state === 'idle' && <span className="text-subtle-foreground">Waiting</span>}
        </span>
        <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: 'easeOut' }}
            className="overflow-hidden border-t border-border"
          >
            <div ref={scrollRef} className="max-h-56 overflow-auto bg-terminal px-4 py-3 font-mono text-[12.5px] leading-relaxed">
              {rows.length > 0 && (
                <div className="mb-3 border-b border-terminal-muted/30 pb-3">
                  <StructuredRows rows={rows} />
                </div>
              )}
              {logs.length === 0 ? (
                <div className="flex items-center gap-2 text-terminal-muted">
                  <span className="text-primary">$</span>
                  <span>Waiting for pipeline activation…</span>
                  <span className="cursor-blink" />
                </div>
              ) : (
                logs.map((log, i) => {
                  const { level, agent, message } = parseLog(log.text)
                  return (
                    <div key={i} className="flex gap-3 whitespace-nowrap">
                      <span className="shrink-0 tabular-nums text-terminal-muted">{log.timestamp}</span>
                      <span className="w-20 shrink-0 truncate text-primary-border">{agent}</span>
                      <span className={levelColor(level)}>{message}</span>
                    </div>
                  )
                })
              )}
              {state === 'running' && logs.length > 0 && (
                <div className="flex gap-3">
                  <span className="shrink-0 text-terminal-muted">…</span>
                  <span className="cursor-blink text-primary" />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}
