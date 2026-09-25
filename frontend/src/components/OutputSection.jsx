import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Mail, Phone, Copy, Check, Send, FileText, ClipboardList } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Badge, SectionHeader, DescriptionList } from './ui'

function CopyButton({ text }) {
  const [ok, setOk] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setOk(true)
      setTimeout(() => setOk(false), 2000)
    } catch (e) {
      console.error(e)
    }
  }
  return (
    <Button variant={ok ? 'secondary' : 'secondary'} size="sm" onClick={copy}>
      {ok ? <><Check className="h-3.5 w-3.5 text-success" />Copied</> : <><Copy className="h-3.5 w-3.5" />Copy</>}
    </Button>
  )
}

const VERDICT_BADGE = { approve: 'success', reject: 'error', flag: 'warning' }

function formatFieldValue(key, value) {
  const k = key.toLowerCase()
  if (typeof value === 'number' && (k.includes('amount') || k.includes('billed') || k.includes('responsibility'))) {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
  }
  return String(value)
}

function labelize(key) {
  return key.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase()).trim()
}

export default function OutputSection({ results }) {
  const [tab, setTab] = useState('email')
  const navigate = useNavigate()

  const tabs = [
    { id: 'email', label: 'Email', Icon: Mail },
    { id: 'whatsapp', label: 'WhatsApp', Icon: Phone },
    { id: 'summary', label: 'Summary', Icon: FileText },
    { id: 'agents', label: 'Findings', Icon: ClipboardList },
  ]

  const copyText =
    tab === 'email' ? results.email :
    tab === 'whatsapp' ? results.whatsapp :
    tab === 'agents' ? JSON.stringify(results.findings, null, 2) :
    JSON.stringify(results.claimData, null, 2)

  const recBadge =
    results.recommendation === 'APPROVE' ? 'success' :
    results.recommendation === 'REJECT' ? 'error' : 'warning'

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-default px-5 py-4">
        <SectionHeader icon={Send} title="Generated outputs" description="Ready-to-send deliverables" />
        <div className="flex items-center gap-2">
          <CopyButton text={copyText} />
          <Button variant="primary" size="sm" onClick={() => navigate('/submission')}>
            Submit claim
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-default" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`relative flex shrink-0 items-center gap-2 px-4 py-3 text-sm font-medium transition-colors cursor-pointer ${
              tab === t.id ? 'text-brand' : 'text-secondary hover:text-primary'
            }`}
          >
            <t.Icon className="h-4 w-4" />
            {t.label}
            {tab === t.id && (
              <motion.span
                layoutId="output-tab-indicator"
                className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-brand"
                transition={{ duration: 0.2 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="max-h-[320px] overflow-y-auto p-5">
        {(tab === 'email' || tab === 'whatsapp') && (
          <div className="rounded-md border border-default bg-subtle p-4">
            <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-secondary">
              {tab === 'email' ? results.email : results.whatsapp}
            </pre>
          </div>
        )}

        {tab === 'summary' && (
          <div>
            <DescriptionList
              items={Object.entries(results.claimData).map(([key, value]) => ({
                label: labelize(key),
                value: formatFieldValue(key, value),
              }))}
            />
            <div className="mt-4 flex items-center justify-between rounded-md border border-default bg-subtle p-4">
              <div>
                <div className="text-xs text-secondary">Recommendation</div>
                <Badge variant={recBadge} className="mt-1">{results.recommendation}</Badge>
              </div>
              <div className="text-right">
                <div className="text-xs text-secondary">Risk score</div>
                <div className="mt-1 text-sm font-semibold text-primary">
                  {results.riskScore} <span className="text-secondary">({results.riskLabel})</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === 'agents' && (
          <div className="space-y-2">
            {(results.findings || []).map((f, i) => (
              <div key={i} className="flex items-start gap-3 rounded-md border border-default p-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold capitalize text-primary">
                      {f.agent.replace(/_/g, ' ')}
                    </span>
                    <Badge variant={VERDICT_BADGE[f.verdict] || 'neutral'}>
                      {f.verdict.toUpperCase()}
                    </Badge>
                    <span className="text-xs text-muted">conf {(f.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-secondary">{f.reasoning}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}
