import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Loader2 } from 'lucide-react'

const insurerNameMap = {
  aetna: 'Aetna Claim Portal Clone',
  uhc: 'UnitedHealthcare Portal Clone',
  bcbs: 'Blue Cross Blue Shield Clone',
}

function buildApplicationNumber(prefix) {
  const rand = Math.floor(100000 + Math.random() * 900000)
  return `${prefix.toUpperCase()}-${new Date().getFullYear()}-${rand}`
}

export default function InsurerPortalPage() {
  const navigate = useNavigate()
  const { insurerId } = useParams()
  const [searchParams] = useSearchParams()
  const autoFill = searchParams.get('autofill') === '1'

  const claim = useMemo(() => {
    try {
      const raw = localStorage.getItem('binaryblitz.latestClaim')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }, [])

  const [form, setForm] = useState({
    patientName: '',
    policyNumber: '',
    dob: '',
    provider: '',
    diagnosisCode: '',
    cptCode: '',
    totalBilled: '',
    approvedAmount: '',
    patientResponsibility: '',
    dateOfService: '',
  })
  const [isFilling, setIsFilling] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [appNumber, setAppNumber] = useState('')

  useEffect(() => {
    if (!claim || !autoFill) return

    const source = claim.claimData || {}
    const steps = [
      ['patientName', source.patientName || ''],
      ['policyNumber', source.policyNumber || ''],
      ['dob', source.dob || ''],
      ['provider', source.provider || ''],
      ['diagnosisCode', source.diagnosisCode || ''],
      ['cptCode', source.cptCode || ''],
      ['totalBilled', String(source.totalBilled ?? '')],
      ['approvedAmount', String(source.approvedAmount ?? '')],
      ['patientResponsibility', String(source.patientResponsibility ?? '')],
      ['dateOfService', source.dateOfService || ''],
    ]

    let idx = 0
    setIsFilling(true)
    const timer = setInterval(() => {
      const current = steps[idx]
      if (!current) {
        clearInterval(timer)
        setIsFilling(false)
        setIsComplete(true)
        const applicationNo = buildApplicationNumber(insurerId || 'ins')
        setAppNumber(applicationNo)
        localStorage.setItem('binaryblitz.lastApplicationNumber', applicationNo)
        return
      }

      setForm((prev) => ({ ...prev, [current[0]]: current[1] }))
      idx += 1
    }, 260)

    return () => clearInterval(timer)
  }, [claim, autoFill, insurerId])

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-base grid-pattern p-5 lg:p-8">
      <div className="max-w-4xl mx-auto space-y-5">
        <button onClick={() => navigate('/submission')} className="flex items-center gap-2 text-sm text-text-dim hover:text-text cursor-pointer">
          <ArrowLeft className="w-4 h-4" /> Back to Submission Hub
        </button>

        <div className="glass p-5">
          <h1 className="text-xl font-bold text-text">{insurerNameMap[insurerId] || 'Insurer Portal Clone'}</h1>
          <p className="text-sm text-text-dim mt-1">Agentic auto-fill from extracted PDF details.</p>

          {!claim && (
            <div className="mt-4 rounded-lg border border-warning/20 bg-warning/10 p-3 text-xs text-warning">
              No local claim snapshot found. Please process a claim first.
            </div>
          )}

          {claim && (
            <div className="mt-5 grid sm:grid-cols-2 gap-3 text-xs text-text-dim">
              {Object.entries(form).map(([key, value]) => (
                <div key={key} className="rounded-lg border border-border p-3 bg-card-solid/50">
                  <div className="capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</div>
                  <div className="text-text font-semibold mt-1">{value || '—'}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="glass p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-text-dim">
            {isFilling ? <Loader2 className="w-4 h-4 animate-spin text-violet" /> : <CheckCircle2 className="w-4 h-4 text-success" />}
            {isFilling ? 'Agent is auto-filling portal form...' : isComplete ? 'Portal form filled successfully' : 'Ready to auto-fill'}
          </div>

          {isComplete && (
            <div className="px-3 py-1.5 rounded-xl bg-success/10 border border-success/30 text-success text-sm font-semibold">
              Application #: {appNumber}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
