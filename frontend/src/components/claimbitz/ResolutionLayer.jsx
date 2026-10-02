import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, AlertTriangle, ArrowRight, Mail, RotateCcw, UserCheck } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * ResolutionLayer — the operational "what happens next" layer between
 * risk assessment and generated outputs.
 *
 * Uses ONLY real data from useClaimAgent results. Actions are limited to
 * functionality that genuinely exists in the application:
 *   onPortal    → navigate to /submission (insurer portal selection)
 *   onReprocess → call reset + re-enable processing
 *
 * Wording is truthful:
 *   "Continue to insurer portal" — NOT "Claim submitted"
 *   "Generate clarification"     — NOT "Clarification sent"
 *   "Human review required"      — NOT "Investigation started"
 */

function deriveAction(recommendation, riskLabel) {
  const rec = (recommendation || '').toUpperCase()
  const label = (riskLabel || '').toUpperCase()

  if (rec === 'APPROVE' || (label === 'LOW' && rec !== 'REJECT' && rec !== 'REVIEW')) {
    return {
      heading: 'Proceed toward submission',
      description: 'The claim passed automated review with no blocking findings. Continue to the insurer portal to prepare the submission.',
      tone: 'success',
      actions: ['portal'],
    }
  }
  if (rec === 'REJECT' || label === 'HIGH') {
    return {
      heading: 'Human review required',
      description: 'The claim exceeds the automated approval threshold. Review the findings and generated communications before deciding on next steps.',
      tone: 'destructive',
      actions: ['communications', 'reprocess'],
    }
  }
  // MEDIUM / REVIEW
  return {
    heading: 'Review and clarification needed',
    description: 'Some findings require attention before the claim can proceed. Generate a clarification request or re-process after addressing the concerns.',
    tone: 'warning',
    actions: ['communications', 'portal', 'reprocess'],
  }
}

function summarizeFindings(findings, riskReasons) {
  const items = []

  if (findings && findings.length > 0) {
    findings.forEach((f) => {
      const v = (f.verdict || '').toLowerCase()
      items.push({
        text: f.reasoning?.slice(0, 90) || `${(f.agent || '').replace(/_/g, ' ')}: ${v}`,
        ok: v === 'approve',
      })
    })
  } else if (riskReasons && riskReasons.length > 0) {
    riskReasons.forEach((r) => {
      const lower = r.toLowerCase()
      const ok = lower.includes('no ') || lower.includes('valid') || lower.includes('in-network') || lower.includes('consistent') || lower.includes('passed')
      items.push({ text: r, ok })
    })
  }

  return items.slice(0, 6)
}

const TONES = {
  success: { bg: 'bg-success-subtle', text: 'text-success', Icon: CheckCircle2 },
  warning: { bg: 'bg-warning-subtle', text: 'text-warning', Icon: AlertTriangle },
  destructive: { bg: 'bg-destructive/10', text: 'text-destructive', Icon: AlertTriangle },
}

export function ResolutionLayer({
  recommendation,
  riskLabel,
  findings,
  riskReasons,
  onPortal,
  onReprocess,
}) {
  if (!recommendation && !riskLabel) return null

  const action = deriveAction(recommendation, riskLabel)
  const items = summarizeFindings(findings, riskReasons)
  const t = TONES[action.tone] || TONES.warning

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.15 }}
      className="panel overflow-hidden"
      aria-label="Recommended action"
    >
      {/* Action heading */}
      <header className="border-b border-border px-5 py-4">
        <p className="eyebrow">Recommended action</p>
        <div className="mt-2 flex items-start gap-3">
          <span className={cn('mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full', t.bg)}>
            <t.Icon className={cn('h-3.5 w-3.5', t.text)} />
          </span>
          <div className="min-w-0">
            <h3 className="text-[15px] font-semibold text-foreground">{action.heading}</h3>
            <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{action.description}</p>
          </div>
        </div>
      </header>

      {/* Key findings */}
      {items.length > 0 && (
        <div className="border-b border-border px-5 py-4">
          <p className="eyebrow mb-2">Key findings</p>
          <ul className="space-y-1.5">
            {items.map((item, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: 0.2 + i * 0.06 }}
                className="flex items-start gap-2 text-[13px]"
              >
                {item.ok ? (
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                ) : (
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
                )}
                <span className="text-muted-foreground">{item.text}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* Available next steps — only genuinely existing actions */}
      <div className="flex flex-wrap items-center gap-3 px-5 py-4">
        {action.actions.includes('portal') && onPortal && (
          <button
            onClick={onPortal}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-[13.5px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98]"
          >
            Continue to insurer portal
            <ArrowRight className="h-4 w-4" />
          </button>
        )}
        {action.actions.includes('communications') && (
          <span className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground">
            <Mail className="h-3.5 w-3.5" />
            Generated communications available below
          </span>
        )}
        {action.actions.includes('reprocess') && onReprocess && (
          <button
            onClick={onReprocess}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-surface px-4 text-[13.5px] font-medium text-foreground transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
          >
            <RotateCcw className="h-3.5 w-3.5 text-muted-foreground" />
            Re-process claim
          </button>
        )}
      </div>
    </motion.section>
  )
}
