import React, { useRef, useEffect, useState } from 'react'
import { Terminal, Minimize2, Maximize2, ChevronDown } from 'lucide-react'

export default function TerminalWindow({ logs, isProcessing }) {
  const scrollRef = useRef(null)
  const [expanded, setExpanded] = useState(true)
  const [maximized, setMaximized] = useState(false)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [logs])

  // Lock body scroll while maximized
  useEffect(() => {
    if (!maximized) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [maximized])

  return (
    <div
      className={`overflow-hidden rounded-lg border border-term-border bg-term-bg ${
        maximized ? 'fixed inset-4 z-[70] shadow-[0_12px_32px_rgba(16,24,40,0.12)]' : ''
      }`}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-term-border px-4 py-2.5">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5" aria-hidden="true">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-600" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-600" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-600" />
          </div>
          <div className="flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5 text-slate-500" />
            <span className="font-mono text-xs text-slate-400">agent_pipeline.log</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMaximized(!maximized)}
            aria-label={maximized ? 'Restore terminal' : 'Maximize terminal'}
            className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200 cursor-pointer"
          >
            {maximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            aria-label={expanded ? 'Collapse terminal' : 'Expand terminal'}
            aria-expanded={expanded}
            className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200 cursor-pointer"
          >
            <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? '' : '-rotate-90'}`} />
          </button>
        </div>
      </div>

      {/* Body */}
      {expanded && (
        <div
          ref={scrollRef}
          className={`overflow-y-auto p-4 ${maximized ? 'h-[calc(100%-45px)]' : 'h-60'}`}
        >
          {logs.length === 0 ? (
            <div className="log-line flex items-center gap-2 text-slate-500">
              <span className="text-brand">$</span>
              <span>Waiting for pipeline activation…</span>
              <span className="cursor-blink" />
            </div>
          ) : (
            <>
              {logs.map((log, i) => (
                <div key={i} className="log-line flex gap-2">
                  <span className="w-7 shrink-0 select-none text-right tabular-nums text-slate-600">
                    {String(i + 1).padStart(3, '0')}
                  </span>
                  <span className="select-none text-slate-700">│</span>
                  <span
                    className={
                      log.text.includes('[SUCCESS]') ? 'text-[#4ADE80]' :
                      log.text.includes('[WARN]') ? 'text-[#FBBF24]' :
                      log.text.includes('[ERROR]') ? 'text-[#F87171]' :
                      log.text.includes('[DATA]') ? 'text-[#818CF8]' :
                      log.text.includes('[SYSTEM]') ? 'text-slate-300' :
                      'text-slate-400'
                    }
                  >
                    <span className="mr-2 text-slate-600">{log.timestamp}</span>
                    {log.text}
                  </span>
                </div>
              ))}
              {isProcessing && (
                <div className="log-line mt-1 flex gap-2">
                  <span className="w-7 shrink-0 select-none text-right tabular-nums text-slate-600">
                    {String(logs.length + 1).padStart(3, '0')}
                  </span>
                  <span className="select-none text-slate-700">│</span>
                  <span className="cursor-blink text-brand" />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
