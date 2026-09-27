import React from 'react'
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar'
import 'react-circular-progressbar/dist/styles.css'
import { Gauge, TrendingDown, Activity, TrendingUp } from 'lucide-react'
import { Card, Badge, SectionHeader, Textarea } from './ui'

/* Semantic risk configuration. Colors map to design tokens. */
function cfg(score) {
  if (score <= 0.3) {
    return {
      color: '#16A34A', trail: '#ECFDF3',
      label: 'Low risk', rec: 'Approve', badge: 'success', Icon: TrendingDown,
    }
  }
  if (score <= 0.6) {
    return {
      color: '#D97706', trail: '#FFF7E6',
      label: 'Medium risk', rec: 'Review', badge: 'warning', Icon: Activity,
    }
  }
  return {
    color: '#DC2626', trail: '#FEF2F2',
    label: 'High risk', rec: 'Reject', badge: 'error', Icon: TrendingUp,
  }
}

export default function RiskMeter({ score, isProcessing, results }) {
  const c = cfg(score)
  const pct = Math.round(score * 100)
  const riskReasons = results?.riskReasons || []
  const model = results?.riskModel
  const analyzing = isProcessing && score === 0

  return (
    <Card className="p-5">
      <SectionHeader
        icon={Gauge}
        title="Rejection risk"
        description="Model-calculated risk assessment"
      />

      <div className="mt-6 flex flex-col items-center">
        {/* Gauge */}
        <div className="h-36 w-36">
          <CircularProgressbar
            value={analyzing ? 0 : pct}
            text={analyzing ? '…' : `${pct}%`}
            strokeWidth={8}
            styles={buildStyles({
              textSize: '20px',
              textColor: '#171717',
              pathColor: c.color,
              trailColor: c.trail,
              pathTransitionDuration: 0.8,
              strokeLinecap: 'round',
            })}
          />
        </div>

        {/* Level */}
        <div className="mt-5 flex items-center gap-2">
          <Badge variant={analyzing ? 'neutral' : c.badge}>
            <c.Icon className="h-3.5 w-3.5" />
            {analyzing ? 'Analyzing…' : c.label}
          </Badge>
        </div>

        {/* Recommendation */}
        {!isProcessing && score > 0 && (
          <p className="mt-2 text-sm text-secondary">
            Recommendation: <span className="font-semibold text-primary">{c.rec}</span>
          </p>
        )}
        {analyzing && (
          <p className="mt-2 text-sm text-secondary">Evaluating risk factors…</p>
        )}
      </div>

      {!isProcessing && results && (
        <div className="mt-6 space-y-4">
          {/* Model breakdown */}
          <div className="rounded-md border border-default bg-subtle p-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Risk model</div>
            <dl className="space-y-1.5 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-secondary">Engine</dt>
                <dd className="font-medium text-primary">{model?.engine || 'rules'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-secondary">Model</dt>
                <dd className="font-mono text-xs font-medium text-primary">{model?.modelName || 'deterministic-rules-v1'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-secondary">Base score</dt>
                <dd className="font-medium text-primary">{model?.baseScore ?? 0}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-secondary">Thresholds</dt>
                <dd className="font-medium text-primary">
                  Low ≤ {model?.thresholds?.lowMax ?? 0.3}, Med ≤ {model?.thresholds?.mediumMax ?? 0.6}
                </dd>
              </div>
            </dl>
          </div>

          {/* High-risk explanation */}
          {results?.riskLabel === 'HIGH' && (
            <div>
              <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-error">
                Why risk is high
              </div>
              <Textarea
                readOnly
                rows={5}
                value={
                  riskReasons.length
                    ? riskReasons.map((r, i) => `${i + 1}. ${r}`).join('\n')
                    : 'No detailed reason returned by backend.'
                }
              />
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
