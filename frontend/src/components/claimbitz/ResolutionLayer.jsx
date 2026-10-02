import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, AlertTriangle, ArrowRight, Mail, MessageSquare } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * ResolutionLayer — the operational "what happens next" layer between
 * risk assessment and generated outputs.
 *
 * Uses ONLY real data from useClaimAgent results:
 *   recommendation   'APPROVE' | 'REVIEW' | 'REJECT' (or absent)
 *   riskLabel        'LOW' | 'MEDIUM' | 'HIGH'
 *   findings         array of { agent, verdict, confidence, reasoning }
 *   riskReasons      string[]
 *
 * Actions exposed are limited to functionality that genuinely exists:
 *   onPortal         navigate to /submission (insurer portal selection)
 *
 * No fake "Approve Claim", "Submit to Insurer", or "Start Investigation"
 * buttons — those would misrepresent the application's real capabilities.
 */

function deriveAction(recommendation, riskLabel) {
  const rec = (recommendation || '').toUpperCase()
  const label = (riskLabel || '').toUpperCase()

  if (rec === 'APPROVE' || label === 'LOW') {
    return {
      heading: 'Proceed with approval',
      description: 'The claim passed automated review. Continue to the insurer portal to prepare submission.',
      tone: 'success',
      actionLabel: 'Continue to insurer portal',
      showPortal: true,
    }
  }
  if (rec === 'REJECT' || label === 'HIGH') {
    return {
      heading: 'Escalate for human review',
      description: 'The claim exceeds the automated threshold. Review the findings and generated communications before deciding.',
      tone: 'destructive',
      actionLabel: 'Review generated communications',
      showPortal: false, // don't encourage portal submission for high-risk
    }
  }
  // MEDIUM / REVIEW / other
  return {
    heading: 'Manual review recommended',
    description: 'Some findings require clarification. Review the details below and determine whether to proceed or request additional information.',
    tone: 'warning',
    actionLabel: 'Continue to insurer portal',
    showPortal: true,
  }
}

function summarizeFindings(findings, riskReasons) {
  const items = []

  // Use findings if available (real backend data)
  if (findings && findings.length > 0) {
    findings.forEach((f) => {
      const v = (f.verdict || '').toLowerCase()
      items.push({
        text: f.reasoning?.slice(0, 80) || `${f.agent}: ${v}`,
        ok: v === 'approve',
      })
    })
  } else if (riskReasons && riskReasons.length > 0) {
    // Fallback to riskReasons strings
    riskReasons.forEach((r) => {
      const lower = r.toLowerCase()
      const ok = lower.includes('no ') || lower.includes('valid') || lower.includes('in-network') || lower.includes('consistent')
      items.push({ text: r, ok })
    })
  }

  return items.slice(0, 5)
}

export function ResolutionLayer({
  recommendation,
  riskLabel,
  findings,
  riskReasons,
  onPortal,
}) {
  const action = deriveAction(recommendation, riskLabel)
  const items = summarizeFindings(findings, riskReasons)

  if (!recommendation && !riskLabel) return null // no result data — render nothing

  const toneClasses = {
    success: { bg: 'bg-success-subtle', border: 'border-success/25', text: 'text-success', icon: CheckCircle2 },
    warning: { bg: 'bg-warning-subtle', border: 'border-warning/30', text: 'text-warning', icon: AlertTriangle },
    destructive: { bg: 'bg-destructive/10', border: 'border-destructive/30', text: 'text-destructive', icon: AlertTriangle },
  }
  const t = toneClasses[action.tone] || toneClasses.warning
  const Icon = t.icon

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.15 }}
      className="panel overflow-hidden"
    >
      <header className="border-b border-border px-5 py-4">
        <p className="eyebrow">Recommended action</p>
        <div className="mt-2 flex items-start gap-3">
          <span className={cn('mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full', t.bg)}>
            <Icon className={cn('h-3.5 w-3.5', t.text)} />
          </span>
          <div className="min-w-0">
            <h3 className="text-[15px] font-semibold text-foreground">{action.heading}</h3>
            <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{action.description}</p>
          </div>
        </div>
      </header>

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

      <div className="flex flex-wrap items-center gap-3 px-5 py-4">
        {action.showPortal && onPortal && (
          <button
            onClick={onPortal}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-[13.5px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98]"
          >
            {action.actionLabel}
            <ArrowRight className="h-4 w-4" />
          </button>
        )}
        {!action.showPortal && (
          <p className="text-[13px] text-muted-foreground">
            Review the generated communications below before taking action.
          </p>
        )}
      </div>
    </motion.section>
  )
}
