import React from 'react'
import { motion } from 'framer-motion'
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar'
import 'react-circular-progressbar/dist/styles.css'
import { Activity, TrendingDown, TrendingUp, Shield } from 'lucide-react'

function cfg(score) {
  if (score <= 0.3) return {
    color: '#4ADE80', trail: 'rgba(74,222,128,0.08)', glow: 'rgba(74,222,128,0.25)',
    label: 'LOW RISK', rec: 'APPROVE', Icon: TrendingDown, text: 'text-success', bg: 'bg-success/8', border: 'border-success/25'
  }
  if (score <= 0.6) return {
    color: '#FACC15', trail: 'rgba(250,204,21,0.08)', glow: 'rgba(250,204,21,0.25)',
    label: 'MEDIUM RISK', rec: 'REVIEW', Icon: Activity, text: 'text-warning', bg: 'bg-warning/8', border: 'border-warning/25'
  }
  return {
    color: '#FB7185', trail: 'rgba(251,113,133,0.08)', glow: 'rgba(251,113,133,0.25)',
    label: 'HIGH RISK', rec: 'REJECT', Icon: TrendingUp, text: 'text-danger', bg: 'bg-danger/8', border: 'border-danger/25'
  }
}

export default function RiskMeter({ score, isProcessing, results }) {
  const c = cfg(score)
  const pct = Math.round(score * 100)
  const riskReasons = results?.riskReasons || []
  const model = results?.riskModel

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }} className="glass p-6">

      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 rounded-xl bg-violet-dim flex items-center justify-center">
          <Shield className="w-4 h-4 text-violet" />
        </div>
        <div>
          <h2 className="font-bold text-text text-sm">Rejection Risk Meter</h2>
          <p className="text-[11px] text-text-dim">AI-calculated risk assessment</p>
        </div>
      </div>

      <div className="flex flex-col items-center">
        {/* Gauge */}
        <div className="relative w-40 h-40 mb-6">
          <div className="absolute inset-2 rounded-full blur-2xl opacity-40" style={{ backgroundColor: c.glow }} />
          <div className="relative z-10">
            <CircularProgressbar
              value={isProcessing && score === 0 ? 0 : pct}
              text={isProcessing && score === 0 ? '...' : `${pct}%`}
              strokeWidth={7}
              styles={buildStyles({
                textSize: '22px',
                textColor: c.color,
                pathColor: c.color,
                trailColor: c.trail,
                pathTransitionDuration: 1.5,
                strokeLinecap: 'round',
              })}
            />
          </div>
        </div>

        {/* Label */}
        <motion.div key={c.label} initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl ${c.bg} border ${c.border} mb-3`}>
          <c.Icon className={`w-4 h-4 ${c.text}`} />
          <span className={`text-sm font-bold ${c.text}`}>{c.label}</span>
        </motion.div>

        {!isProcessing && score > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="text-center">
            <span className="text-[11px] text-text-dim">Recommendation: </span>
            <span className={`text-[11px] font-bold ${c.text}`}>{c.rec}</span>
          </motion.div>
        )}
        {isProcessing && score === 0 && (
          <div className="text-[11px] text-text-dim animate-pulse">Analyzing risk factors...</div>
        )}
      </div>

      {!isProcessing && results && (
        <div className="mt-5 space-y-3">
          <div className="rounded-xl border border-border bg-card-solid/50 p-3">
            <div className="text-[11px] font-semibold text-text mb-2">Exact Risk Model</div>
            <div className="text-[11px] text-text-dim leading-relaxed">
              <div>Engine: {model?.engine || 'rules'}</div>
              <div>Model: {model?.modelName || 'deterministic-rules-v1'}</div>
              <div>Base Score: {model?.baseScore ?? 0}</div>
              <div>Issue Penalty: {model?.issuePenaltyPerItem ?? 0} per issue (max {model?.maxIssuePenalty ?? 0})</div>
              <div>Thresholds: LOW ≤ {model?.thresholds?.lowMax ?? 0.3}, MEDIUM ≤ {model?.thresholds?.mediumMax ?? 0.6}, HIGH &gt; {model?.thresholds?.mediumMax ?? 0.6}</div>
            </div>
          </div>

          {results?.riskLabel === 'HIGH' && (
            <div className="rounded-xl border border-danger/30 bg-danger/5 p-3">
              <div className="text-[11px] font-semibold text-danger mb-2">Why Risk Is High (Before Submission)</div>
              <textarea
                readOnly
                className="w-full min-h-[120px] rounded-lg border border-danger/20 bg-[#080D1B] p-3 text-xs text-text-dim resize-y"
                value={riskReasons.length ? riskReasons.map((r, i) => `${i + 1}. ${r}`).join('\n') : 'No detailed reason returned by backend.'}
              />
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}
