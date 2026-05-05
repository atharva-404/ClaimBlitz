import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ScanLine, ShieldCheck, Activity, MessageSquare,
  CheckCircle2, Loader2, Circle, ChevronDown, ChevronUp, Cpu
} from 'lucide-react'

const ICONS = { ScanLine, ShieldCheck, Activity, MessageSquare }

const STATUS = {
  idle:       { color: 'text-text-dim',  bg: 'bg-card-solid/50', border: 'border-border',       Icon: Circle },
  processing: { color: 'text-violet',    bg: 'bg-violet-dim',    border: 'border-violet/40',     Icon: Loader2 },
  completed:  { color: 'text-success',   bg: 'bg-success/8',     border: 'border-success/25',    Icon: CheckCircle2 },
  error:      { color: 'text-danger',    bg: 'bg-danger/8',      border: 'border-danger/25',     Icon: Circle },
}

function AgentCard({ agent, index }) {
  const [open, setOpen] = useState(false)
  const cfg = STATUS[agent.status]
  const AgentIcon = ICONS[agent.icon]

  return (
    <motion.div layout
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={`glass overflow-hidden ${agent.status === 'processing' ? 'neon-active' : ''}`}>
      {/* Header */}
      <div className="p-4 flex items-center gap-3.5 cursor-pointer select-none"
        onClick={() => agent.logs.length > 0 && setOpen(!open)}>

        {/* Step connector */}
        <div className="relative flex flex-col items-center">
          {index > 0 && (
            <div className={`absolute -top-4 w-px h-4 ${
              agent.status === 'completed' ? 'bg-success/40' :
              agent.status === 'processing' ? 'bg-violet/40' : 'bg-border'}`} />
          )}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${cfg.bg} border ${cfg.border} ${
            agent.status === 'processing' ? 'agent-pulse' : ''} transition-all`}>
            {agent.status === 'processing'
              ? <Loader2 className={`w-5 h-5 ${cfg.color} animate-spin`} />
              : agent.status === 'completed'
                ? <CheckCircle2 className={`w-5 h-5 ${cfg.color}`} />
                : <AgentIcon className={`w-5 h-5 ${cfg.color}`} />}
          </div>
          {index < 3 && (
            <div className={`absolute -bottom-4 w-px h-4 ${
              agent.status === 'completed' ? 'bg-success/40' : 'bg-border'}`} />
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className={`font-semibold text-sm ${agent.status === 'idle' ? 'text-text-dim' : 'text-text'}`}>
              {agent.name}
            </h3>
            {agent.status === 'processing' && (
              <motion.span initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: 1 }}
                className="text-[9px] px-2 py-0.5 rounded-md bg-violet-dim text-violet font-bold tracking-widest">ACTIVE</motion.span>
            )}
            {agent.status === 'completed' && (
              <motion.span initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: 1 }}
                className="text-[9px] px-2 py-0.5 rounded-md bg-success/10 text-success font-bold tracking-widest">DONE</motion.span>
            )}
          </div>
          <p className="text-[11px] text-text-dim mt-0.5 truncate">{agent.description}</p>
        </div>

        {agent.logs.length > 0 && (
          <div className="p-1 rounded-lg hover:bg-white/5 transition-colors">
            {open ? <ChevronUp className="w-4 h-4 text-text-dim/40" /> : <ChevronDown className="w-4 h-4 text-text-dim/40" />}
          </div>
        )}
      </div>

      {/* Log Console */}
      <AnimatePresence>
        {open && agent.logs.length > 0 && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }} className="overflow-hidden">
            <div className="px-4 pb-4">
              <div className="bg-[#080D1B] rounded-xl p-3 max-h-36 overflow-y-auto border border-white/[0.04]">
                {agent.logs.map((log, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.015 }} className="log-line">
                    <span className={
                      log.includes('[SUCCESS]') ? 'text-success' :
                      log.includes('[WARN]')    ? 'text-warning' :
                      log.includes('[ERROR]')   ? 'text-danger' :
                      log.includes('[DATA]')    ? 'text-cyan' :
                      'text-text-dim/50'}>
                      {log}
                    </span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function AgentStepper({ agents, currentStep }) {
  return (
    <div className="glass p-4 sm:p-5">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-9 h-9 rounded-xl bg-violet-dim flex items-center justify-center">
          <Cpu className="w-[18px] h-[18px] text-violet" />
        </div>
        <div>
          <h2 className="font-bold text-text text-sm">Agent Command Center</h2>
          <p className="text-[11px] text-text-dim">4-agent autonomous pipeline</p>
        </div>
      </div>
      <div className="space-y-3">
        {agents.map((agent, i) => <AgentCard key={agent.id} agent={agent} index={i} />)}
      </div>
    </div>
  )
}
