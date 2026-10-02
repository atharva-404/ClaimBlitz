import React from 'react'
import { motion } from 'framer-motion'
import { Info, Send, ShieldAlert, ShieldCheck } from 'lucide-react'
import { RiskRing, AnimatedPercent } from './RiskRing'
import { cn } from '../../lib/utils'

const DIMENSION_LABELS = {
  documentation_risk: 'Documentation',
  policy_risk: 'Policy',
  clinical_risk: 'Clinical',
  billing_risk: 'Billing',
  fraud_risk: 'Fraud',
  overall_review_risk: 'Overall review',
}

function bandTone(band) {
  const b = (band || '').toLowerCase()
  if (b === 'high') return 'bg-destructive'
  if (b === 'medium') return 'bg-warning'
  return 'bg-success'
}

/** The six decomposed risk dimensions as a compact bar list (design §13.3). */
function RiskDimensions({ riskBreakdown }) {
  if (!riskBreakdown) return null
  const dims = [
    'documentation_risk', 'policy_risk', 'clinical_risk',
    'billing_risk', 'fraud_risk', 'overall_review_risk',
  ]
    .map((k) => ({ key: k, dim: riskBreakdown[k] }))
    .filter((d) => d.dim && typeof d.dim.score === 'number')
  if (dims.length === 0) return null

  return (
    <div className="rounded-md border border-border bg-surface-muted" aria-label="Risk dimensions">
      <p className="border-b border-border px-3.5 py-2 text-[11px] font-semibold uppercase tracking-wide text-subtle-foreground">
        Risk dimensions
      </p>
      <ul className="divide-y divide-border">
        {dims.map(({ key, dim }) => {
          const pct = Math.round((dim.score || 0) * 100)
          return (
            <li key={key} className="px-3.5 py-2">
              <div className="flex items-center justify-between gap-3 text-[12px]">
                <span className="flex items-center gap-1.5 font-medium text-foreground">
                  {DIMENSION_LABELS[key] || key}
                  {dim.blocking && (
                    <span className="rounded bg-destructive/10 px-1 py-0.5 text-[9px] font-bold uppercase text-destructive">
                      blocking
                    </span>
                  )}
                </span>
                <span className="tabular-nums text-muted-foreground">{pct}% · {dim.band}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-border/60" aria-hidden>
                <div className={cn('h-full rounded-full', bandTone(dim.band))} style={{ width: `${pct}%` }} />
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/**
 * Risk & decision panel — Lovable visual, REAL data.
 *
 * Props come straight from useClaimAgent results:
 *   score        0..1 rejection risk (riskScore)
 *   label        'LOW' | 'MEDIUM' | 'HIGH' (riskLabel)
 *   recommendation  'APPROVE' | 'REJECT' | 'REVIEW'
 *   reasons      string[] (riskReasons)
 *   onSubmit     navigate to submission
 */
function bandFor(score, label) {
  const l = (label || '').toUpperCase()
  if (l === 'HIGH' || score > 0.6) return { tone: 'destructive', high: true, readable: 'High risk' }
  if (l === 'MEDIUM' || score > 0.3) return { tone: 'warning', high: false, readable: 'Medium risk' }
  return { tone: 'success', high: false, readable: 'Low risk' }
}

export function RiskPanel({
  score = 0,
  label,
  recommendation,
  reasons = [],
  onSubmit,
  decision = null,
  riskBreakdown = null,
}) {
  const pct = Math.round((score || 0) * 100)
  const band = bandFor(score, label)
  const rec = recommendation || (band.high ? 'REVIEW' : 'APPROVE')
  const blockingConditions = decision?.blockingConditions || []
  const basis = decision?.basis || []

  return (
    <section className="panel overflow-hidden">
      <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-[19px] font-semibold text-foreground">Risk &amp; decision</h2>
          <p className="mt-0.5 text-[13px] text-muted-foreground">Model-based rejection risk assessment</p>
        </div>
        <span
          className={cn(
            'inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-semibold uppercase tracking-wide',
            band.high ? 'bg-destructive/10 text-destructive' : band.tone === 'warning' ? 'bg-warning-subtle text-warning' : 'bg-success-subtle text-success',
          )}
        >
          {band.high ? <ShieldAlert className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
          {band.readable}
        </span>
      </header>

      <div className="grid gap-6 px-5 py-5 md:grid-cols-[auto_1fr] md:items-center">
        <div className="flex items-center gap-5">
          <div className="relative">
            <RiskRing value={pct} tone={band.tone} />
            <div className="absolute inset-0 flex items-center justify-center">
              <AnimatedPercent value={pct} className="text-2xl font-semibold tracking-tight text-foreground" />
            </div>
          </div>
          <div className="min-w-0">
            <p className="text-[15px] font-semibold text-foreground">
              {band.high ? 'Human review required' : 'Automated review complete'}
            </p>
            <p className="mt-1 max-w-[16rem] text-[13px] text-muted-foreground">
              {band.high
                ? 'The claim exceeds the automated approval threshold.'
                : 'Below the automated approval threshold.'}
            </p>
            <button
              onClick={onSubmit}
              className={cn(
                'mt-3 inline-flex h-9 items-center gap-1.5 rounded-md px-3.5 text-[13px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98]',
                band.high
                  ? 'border border-border bg-surface text-foreground hover:bg-surface-muted'
                  : 'bg-primary text-white hover:bg-primary-hover',
              )}
            >
              <Send className="h-4 w-4" />
              {band.high ? 'Review before submission' : 'Continue to submission'}
            </button>
          </div>
        </div>

        <div className="rounded-md border border-border bg-surface-muted">
          <p className="border-b border-border px-3.5 py-2 text-[11px] font-semibold uppercase tracking-wide text-subtle-foreground">
            Decision
          </p>
          <div className="flex items-center justify-between gap-4 px-3.5 py-2.5">
            <span className="text-[13px] text-muted-foreground">Recommendation</span>
            <span
              className={cn(
                'rounded px-2 py-0.5 text-[12px] font-bold uppercase tracking-wide',
                rec === 'APPROVE' ? 'bg-success-subtle text-success' : rec === 'REJECT' ? 'bg-destructive/10 text-destructive' : 'bg-warning-subtle text-warning',
              )}
            >
              {rec}
            </span>
          </div>

          {reasons.length > 0 && (
            <dl className="divide-y divide-border border-t border-border">
              {reasons.slice(0, 5).map((r, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.28, delay: 0.15 + i * 0.05 }}
                  className="px-3.5 py-2 text-[12.5px] leading-relaxed text-muted-foreground"
                >
                  {r}
                </motion.div>
              ))}
            </dl>
          )}
        </div>
      </div>

      {/* Decision explanation + basis — the % is display-only, not the gate. */}
      <div className="space-y-4 border-t border-border px-5 py-5">
        <p className="flex items-start gap-2 rounded-md border border-border bg-surface-muted px-3.5 py-2.5 text-[12.5px] leading-relaxed text-muted-foreground">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-subtle-foreground" aria-hidden />
          <span>
            <span className="font-semibold text-foreground">Review risk: {pct}%</span> is{' '}
            <code className="rounded bg-surface px-1 text-[11px]">overall_review_risk.score</code> — a
            display-only indicator, not the decision gate. The decision below comes from the Judge's
            reconciliation of the agent findings and any blocking conditions.
          </span>
        </p>

        <RiskDimensions riskBreakdown={riskBreakdown} />

        {basis.length > 0 && (
          <div className="rounded-md border border-border">
            <p className="border-b border-border px-3.5 py-2 text-[11px] font-semibold uppercase tracking-wide text-subtle-foreground">
              Decision basis
            </p>
            <ul className="divide-y divide-border">
              {basis.map((b, i) => (
                <li key={i} className="px-3.5 py-2 text-[12.5px]">
                  <span className="font-medium capitalize text-foreground">{String(b.source || '').replace(/_/g, ' ')}</span>
                  <span className="ml-2 text-muted-foreground">{b.evidence}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {blockingConditions.length > 0 && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3.5 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-destructive">Blocking conditions</p>
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {blockingConditions.map((c, i) => (
                <li
                  key={i}
                  className="rounded bg-destructive/10 px-1.5 py-0.5 text-[11px] font-medium text-destructive"
                >
                  {String(c).replace(/_/g, ' ')}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
