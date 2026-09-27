import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, Check, CheckCircle2, Copy, Mail, MessageSquare, FileText, ClipboardList } from 'lucide-react'
import { cn } from '../../lib/utils'

const TABS = [
  { id: 'email', label: 'Email', Icon: Mail },
  { id: 'whatsapp', label: 'WhatsApp', Icon: MessageSquare },
  { id: 'summary', label: 'Summary', Icon: FileText },
  { id: 'findings', label: 'Findings', Icon: ClipboardList },
]

const VERDICT = {
  approve: 'bg-success-subtle text-success',
  reject: 'bg-destructive/10 text-destructive',
  flag: 'bg-warning-subtle text-warning',
}

function labelize(key) {
  return key.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase()).trim()
}

function formatValue(key, value) {
  const k = key.toLowerCase()
  if (typeof value === 'number' && (k.includes('amount') || k.includes('billed') || k.includes('responsibility'))) {
    return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
  }
  return String(value)
}

/**
 * Generated outputs — Lovable visual, REAL data from useClaimAgent results:
 * email / whatsapp drafts, claim summary (claimData) and agent findings.
 * Submit action navigates to the real submission flow.
 */
export function GeneratedOutput({ results, onSubmit }) {
  const [tab, setTab] = useState('email')
  const [copied, setCopied] = useState(false)

  const high = (results.riskLabel || '').toUpperCase() === 'HIGH'
  const copyText =
    tab === 'email' ? results.email || '' :
    tab === 'whatsapp' ? results.whatsapp || '' :
    tab === 'findings' ? JSON.stringify(results.findings, null, 2) :
    JSON.stringify(results.claimData, null, 2)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="panel overflow-hidden"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3.5">
        <div>
          <h2 className="text-[19px] font-semibold text-foreground">Generated outputs</h2>
          <p className="mt-0.5 text-[13px] text-muted-foreground">Agent-authored result with full audit trail</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copy}
            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-surface-muted"
          >
            {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={onSubmit}
            className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3.5 text-[13px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
          >
            Submit claim
          </button>
        </div>
      </header>

      <div className="flex gap-1 border-b border-border bg-surface-muted px-3 py-2" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'relative inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors',
              tab === t.id ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {tab === t.id && (
              <motion.span
                layoutId="dash-output-tab"
                className="absolute inset-0 rounded-md bg-surface shadow-panel"
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative flex items-center gap-1.5">
              <t.Icon className="h-3.5 w-3.5" />
              {t.label}
            </span>
          </button>
        ))}
      </div>

      <div className="px-5 py-5">
        <div
          className={cn(
            'mb-4 flex items-center gap-2 rounded-md border px-3.5 py-2.5',
            high ? 'border-warning/30 bg-warning-subtle' : 'border-success/25 bg-success-subtle',
          )}
        >
          {high ? <AlertTriangle className="h-4 w-4 text-warning" /> : <CheckCircle2 className="h-4 w-4 text-success" />}
          <p className="text-[13px] font-medium text-foreground">
            {high
              ? `Claim processed · ${Math.round((results.riskScore || 0) * 100)}% risk · human review recommended`
              : `Claim processed · recommendation ${results.recommendation || 'APPROVE'}`}
          </p>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.22 }}
            className="max-h-[320px] overflow-y-auto"
          >
            {(tab === 'email' || tab === 'whatsapp') && (
              <div className="rounded-md border border-border bg-surface-muted p-4">
                <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted-foreground">
                  {tab === 'email' ? results.email : results.whatsapp}
                </pre>
              </div>
            )}

            {tab === 'summary' && (
              <dl className="divide-y divide-border">
                {Object.entries(results.claimData || {}).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-4 py-2.5">
                    <dt className="text-[13px] text-muted-foreground">{labelize(key)}</dt>
                    <dd className="text-[13px] font-medium text-foreground text-right break-words">
                      {formatValue(key, value)}
                    </dd>
                  </div>
                ))}
                <div className="flex items-center justify-between gap-4 pt-3">
                  <dt className="text-[13px] text-muted-foreground">Recommendation</dt>
                  <dd className="text-[13px] font-semibold text-foreground">
                    {results.recommendation} · {results.riskScore} ({results.riskLabel})
                  </dd>
                </div>
              </dl>
            )}

            {tab === 'findings' && (
              <div className="space-y-2">
                {(results.findings || []).map((f, i) => (
                  <div key={i} className="rounded-md border border-border p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] font-semibold capitalize text-foreground">
                        {f.agent.replace(/_/g, ' ')}
                      </span>
                      <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-bold uppercase', VERDICT[f.verdict] || 'bg-surface-muted text-muted-foreground')}>
                        {f.verdict}
                      </span>
                      <span className="text-[11px] text-subtle-foreground">conf {(f.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">{f.reasoning}</p>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.section>
  )
}
