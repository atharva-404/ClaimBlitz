import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ScanLine, ShieldCheck, Activity, MessageSquare,
  CheckCircle2, Loader2, Circle, XCircle, ChevronDown, Workflow,
} from 'lucide-react'
import { Card, Badge, SectionHeader } from './ui'

const ICONS = { ScanLine, ShieldCheck, Activity, MessageSquare }

const STATUS = {
  idle: { label: 'Pending', badge: 'neutral', dot: 'bg-muted', icon: 'text-muted', border: 'border-default', bg: 'bg-surface' },
  processing: { label: 'Processing', badge: 'info', dot: 'bg-brand', icon: 'text-brand', border: 'border-brand-border', bg: 'bg-brand-subtle' },
  completed: { label: 'Completed', badge: 'success', dot: 'bg-success', icon: 'text-success', border: 'border-default', bg: 'bg-surface' },
  error: { label: 'Failed', badge: 'error', dot: 'bg-error', icon: 'text-error', border: 'border-error/40', bg: 'bg-surface' },
}

function AgentRow({ agent, index, isLast }) {
  const [open, setOpen] = useState(false)
  const cfg = STATUS[agent.status] || STATUS.idle
  const AgentIcon = ICONS[agent.icon] || Circle
  const hasLogs = agent.logs.length > 0

  return (
    <li className="relative pl-9">
      {/* Timeline connector */}
      {!isLast && (
        <span
          className={`absolute left-[15px] top-8 h-[calc(100%-1rem)] w-px ${
            agent.status === 'completed' ? 'bg-success/40' : 'bg-default'
          }`}
          aria-hidden="true"
        />
      )}

      {/* Node */}
      <span
        className={`absolute left-0 top-1 flex h-8 w-8 items-center justify-center rounded-full border bg-surface ${cfg.border}`}
      >
        {agent.status === 'processing' ? (
          <Loader2 className={`h-4 w-4 ${cfg.icon} motion-safe:animate-spin`} />
        ) : agent.status === 'completed' ? (
          <CheckCircle2 className={`h-4 w-4 ${cfg.icon}`} />
        ) : agent.status === 'error' ? (
          <XCircle className={`h-4 w-4 ${cfg.icon}`} />
        ) : (
          <AgentIcon className={`h-4 w-4 ${cfg.icon}`} />
        )}
      </span>

      <div className={`rounded-md border ${cfg.border} ${cfg.bg}`}>
        <button
          type="button"
          onClick={() => hasLogs && setOpen(!open)}
          className={`flex w-full items-start gap-3 px-3 py-2.5 text-left ${
            hasLogs ? 'cursor-pointer' : 'cursor-default'
          }`}
          aria-expanded={hasLogs ? open : undefined}
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${agent.status === 'idle' ? 'text-secondary' : 'text-primary'}`}>
                {agent.name}
              </span>
              <Badge variant={cfg.badge}>{cfg.label}</Badge>
            </div>
            <p className="mt-0.5 truncate text-xs text-muted">{agent.description}</p>
          </div>
          {hasLogs && (
            <ChevronDown
              className={`mt-0.5 h-4 w-4 shrink-0 text-muted transition-transform ${open ? 'rotate-180' : ''}`}
            />
          )}
        </button>

        <AnimatePresence initial={false}>
          {open && hasLogs && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="overflow-hidden"
            >
              <div className="px-3 pb-3">
                <div className="max-h-36 overflow-y-auto rounded-md border border-term-border bg-term-bg p-3">
                  {agent.logs.map((log, i) => (
                    <div key={i} className="log-line">
                      <span
                        className={
                          log.includes('[SUCCESS]') ? 'text-[#4ADE80]' :
                          log.includes('[WARN]') ? 'text-[#FBBF24]' :
                          log.includes('[ERROR]') ? 'text-[#F87171]' :
                          log.includes('[DATA]') ? 'text-[#E8965A]' :
                          'text-slate-400'
                        }
                      >
                        {log}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </li>
  )
}

export default function AgentStepper({ agents, demoMode }) {
  return (
    <Card className="p-5">
      <SectionHeader
        icon={Workflow}
        title="Processing timeline"
        description="Collaborative agent pipeline"
        actions={demoMode ? <Badge variant="brand">Demo data</Badge> : null}
      />
      <ol className="mt-5 space-y-3">
        {agents.map((agent, i) => (
          <AgentRow key={agent.id} agent={agent} index={i} isLast={i === agents.length - 1} />
        ))}
      </ol>
    </Card>
  )
}
