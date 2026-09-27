import React, { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, ChevronDown, Loader2, Terminal } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * Processing logs — Lovable visual, REAL data.
 * `logs` is the live terminalLogs array from useClaimAgent ({ text, timestamp }).
 * `state`: 'idle' | 'running' | 'complete' | 'failed'
 */
export function ProcessingLogs({ logs = [], state = 'idle' }) {
  const [open, setOpen] = useState(true)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [logs])

  const colorFor = (text) =>
    text.includes('[SUCCESS]') ? 'text-[#4ADE80]' :
    text.includes('[WARN]') ? 'text-[#FBBF24]' :
    text.includes('[ERROR]') ? 'text-[#F87171]' :
    text.includes('[DATA]') ? 'text-[#E8965A]' :
    text.includes('[SYSTEM]') ? 'text-terminal-foreground' :
    'text-terminal-foreground/70'

  return (
    <section className="panel overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left transition-colors hover:bg-surface-muted"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2.5">
          <Terminal className="h-4 w-4 text-muted-foreground" />
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
              {logs.length === 0 ? (
                <div className="flex items-center gap-2 text-terminal-muted">
                  <span className="text-primary">$</span>
                  <span>Waiting for pipeline activation…</span>
                  <span className="cursor-blink" />
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex gap-3 whitespace-nowrap">
                    <span className="shrink-0 tabular-nums text-terminal-muted">{log.timestamp}</span>
                    <span className={colorFor(log.text)}>{log.text}</span>
                  </div>
                ))
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
