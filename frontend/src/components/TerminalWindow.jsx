import React, { useRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Terminal, Minimize2, Maximize2, ChevronDown, ChevronUp } from 'lucide-react'

export default function TerminalWindow({ logs, isProcessing }) {
  const scrollRef = useRef(null)
  const [expanded, setExpanded] = useState(true)
  const [maximized, setMaximized] = useState(false)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [logs])

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.15 }}
      className={`glass overflow-hidden ${maximized ? 'fixed inset-4 z-[60]' : ''}`}
      style={{ borderRadius: maximized ? '18px' : undefined }}>

      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#080D1B] border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#FF5F57]" />
            <div className="w-3 h-3 rounded-full bg-[#FEBC2E]" />
            <div className="w-3 h-3 rounded-full bg-[#28C840]" />
          </div>
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-text-dim/40" />
            <span className="text-[11px] text-text-dim/50 font-mono">agent_pipeline.log</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setMaximized(!maximized)} className="p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
            {maximized ? <Minimize2 className="w-3.5 h-3.5 text-text-dim/40" /> : <Maximize2 className="w-3.5 h-3.5 text-text-dim/40" />}
          </button>
          <button onClick={() => setExpanded(!expanded)} className="p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
            {expanded ? <ChevronDown className="w-3.5 h-3.5 text-text-dim/40" /> : <ChevronUp className="w-3.5 h-3.5 text-text-dim/40" />}
          </button>
        </div>
      </div>

      {/* Body */}
      {expanded && (
        <div ref={scrollRef}
          className={`bg-[#080D1B] p-4 overflow-y-auto ${maximized ? 'h-[calc(100%-44px)]' : 'h-60'}`}>
          {logs.length === 0 ? (
            <div className="flex items-center gap-2 text-text-dim/25 log-line">
              <span className="text-violet/30">$</span>
              <span>Waiting for pipeline activation...</span>
              <span className="cursor-blink" />
            </div>
          ) : (
            <>
              {logs.map((log, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.12 }} className="log-line flex gap-2">
                  <span className="text-text-dim/15 select-none w-7 text-right shrink-0 tabular-nums">
                    {String(i + 1).padStart(3, '0')}
                  </span>
                  <span className="text-white/[0.06] select-none">│</span>
                  <span className={
                    log.text.includes('[SUCCESS]') ? 'text-success' :
                    log.text.includes('[WARN]')    ? 'text-warning' :
                    log.text.includes('[ERROR]')   ? 'text-danger' :
                    log.text.includes('[DATA]')    ? 'text-cyan' :
                    log.text.includes('[SYSTEM]')  ? 'text-text/60' :
                    'text-text-dim/40'}>
                    <span className="text-text-dim/15 mr-2">{log.timestamp}</span>
                    {log.text}
                  </span>
                </motion.div>
              ))}
              {isProcessing && (
                <div className="log-line flex gap-2 mt-1">
                  <span className="text-text-dim/15 select-none w-7 text-right shrink-0 tabular-nums">
                    {String(logs.length + 1).padStart(3, '0')}
                  </span>
                  <span className="text-white/[0.06] select-none">│</span>
                  <span className="text-violet/50 cursor-blink" />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </motion.div>
  )
}
