import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Mail, Phone, Copy, Check, Send, FileText } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 2000) }
    catch (e) { console.error(e) }
  }
  return (
    <motion.button onClick={copy} whileTap={{ scale: 0.93 }}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
        ok ? 'bg-success/8 border border-success/25 text-success' :
        'bg-card-solid/60 border border-border text-text-dim hover:border-violet/30 hover:text-violet'}`}>
      {ok ? <><Check className="w-3.5 h-3.5" />Copied!</> : <><Copy className="w-3.5 h-3.5" />Copy</>}
    </motion.button>
  )
}

export default function OutputSection({ results }) {
  const [tab, setTab] = useState('email')
  const navigate = useNavigate()

  const tabs = [
    { id: 'email', label: 'Email Draft', Icon: Mail },
    { id: 'whatsapp', label: 'WhatsApp', Icon: Phone },
    { id: 'summary', label: 'Claim Summary', Icon: FileText },
    { id: 'agents', label: 'Agent Findings', Icon: FileText },
  ]

  const content = tab === 'email' ? results.email :
                  tab === 'whatsapp' ? results.whatsapp :
                  tab === 'agents' ? JSON.stringify(results.findings, null, 2) :
                  JSON.stringify(results.claimData, null, 2)

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2, ease: [0.16, 1, 0.3, 1] }} className="glass overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-violet-dim flex items-center justify-center">
            <Send className="w-4 h-4 text-violet" />
          </div>
          <div>
            <h2 className="font-bold text-text text-sm">Actionable Output</h2>
            <p className="text-[11px] text-text-dim">Auto-drafted communications</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/submission')}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-violet-dim border border-violet/30 text-violet hover:opacity-90 transition-all cursor-pointer"
          >
            Submit Claim
          </button>
          <CopyBtn text={content} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border overflow-x-auto">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`shrink-0 flex items-center gap-2 px-4 py-3 text-xs font-medium transition-all relative cursor-pointer ${
              tab === t.id ? 'text-violet' : 'text-text-dim hover:text-text'}`}>
            <t.Icon className="w-3.5 h-3.5" />{t.label}
            {tab === t.id && (
              <motion.div layoutId="tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-violet rounded-full"
                transition={{ duration: 0.25 }} />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 sm:p-5 max-h-[280px] overflow-y-auto">
        {(tab === 'email' || tab === 'whatsapp') && (
          <motion.div key={tab} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="bg-[#080D1B] rounded-xl p-4 border border-white/[0.04]">
            <pre className="text-xs text-text-dim/70 whitespace-pre-wrap font-mono leading-relaxed">
              {tab === 'email' ? results.email : results.whatsapp}
            </pre>
          </motion.div>
        )}

        {tab === 'summary' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2.5">
            {Object.entries(results.claimData).map(([key, value]) => (
              <div key={key} className="flex justify-between items-center py-2 border-b border-white/[0.04] last:border-0">
                <span className="text-xs text-text-dim capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</span>
                <span className="text-xs text-text font-medium font-mono">
                  {typeof value === 'number' && (key.toLowerCase().includes('amount') || key.toLowerCase().includes('billed') || key.toLowerCase().includes('responsibility'))
                    ? `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : String(value)}
                </span>
              </div>
            ))}
            <div className="mt-4 pt-4 border-t border-white/[0.08] flex items-center justify-between">
              <div><span className="text-[11px] text-text-dim">Recommendation</span><div className="text-sm font-bold text-success">{results.recommendation}</div></div>
              <div className="text-right"><span className="text-[11px] text-text-dim">Risk Score</span><div className="text-sm font-bold text-success">{results.riskScore} ({results.riskLabel})</div></div>
            </div>
          </motion.div>
        )}

        {tab === 'agents' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
            {(results.findings || []).map((f, i) => (
              <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border ${
                f.verdict === 'approve' ? 'border-success/20 bg-success/5' :
                f.verdict === 'reject' ? 'border-danger/20 bg-danger/5' :
                'border-warning/20 bg-warning/5'}`}>
                <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                  f.verdict === 'approve' ? 'bg-success' :
                  f.verdict === 'reject' ? 'bg-danger' : 'bg-warning'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-text capitalize">{f.agent.replace('_', ' ')}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      f.verdict === 'approve' ? 'bg-success/10 text-success' :
                      f.verdict === 'reject' ? 'bg-danger/10 text-danger' :
                      'bg-warning/10 text-warning'}`}>{f.verdict.toUpperCase()}</span>
                    <span className="text-[10px] text-text-dim">conf: {(f.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-[11px] text-text-dim leading-relaxed truncate">{f.reasoning}</p>
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}
