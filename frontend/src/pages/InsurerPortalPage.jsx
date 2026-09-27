import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Loader2, Building2 } from 'lucide-react'
import { Card, Badge, Input, SectionHeader, ErrorState } from '../components/ui'

const insurerNameMap = {
  aetna: 'Aetna Claim Portal',
  uhc: 'UnitedHealthcare Portal',
  bcbs: 'Blue Cross Blue Shield',
}

// Preserve backward-compatible localStorage keys written elsewhere.
const LATEST_CLAIM_KEY = 'binaryblitz.latestClaim'
const LAST_APP_NUMBER_KEY = 'binaryblitz.lastApplicationNumber'

const FIELD_LABELS = {
  patientName: 'Patient name',
  policyNumber: 'Policy number',
  dob: 'Date of birth',
  provider: 'Provider',
  diagnosisCode: 'Diagnosis code',
  cptCode: 'CPT code',
  totalBilled: 'Total billed',
  approvedAmount: 'Approved amount',
  patientResponsibility: 'Patient responsibility',
  dateOfService: 'Date of service',
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
      const raw = localStorage.getItem(LATEST_CLAIM_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }, [])

  const [form, setForm] = useState({
    patientName: '', policyNumber: '', dob: '', provider: '', diagnosisCode: '',
    cptCode: '', totalBilled: '', approvedAmount: '', patientResponsibility: '', dateOfService: '',
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
        localStorage.setItem(LAST_APP_NUMBER_KEY, applicationNo)
        return
      }
      setForm((prev) => ({ ...prev, [current[0]]: current[1] }))
      idx += 1
    }, 260)

    return () => clearInterval(timer)
  }, [claim, autoFill, insurerId])

  const statusVariant = isFilling ? 'info' : isComplete ? 'success' : 'neutral'
  const statusLabel = isFilling ? 'Auto-filling…' : isComplete ? 'Submitted' : 'Ready'

  return (
    <div className="min-h-screen bg-canvas">
      {/* Enterprise portal header */}
      <header className="border-b border-default bg-surface">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-5 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-subtle">
              <Building2 className="h-5 w-5 text-brand" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-foreground">
                {insurerNameMap[insurerId] || 'Insurer Portal'}
              </h1>
              <p className="text-xs text-subtle-foreground">Provider claim intake</p>
            </div>
          </div>
          <Badge variant={statusVariant}>
            {isFilling ? <Loader2 className="h-3 w-3 motion-safe:animate-spin" /> : isComplete ? <CheckCircle2 className="h-3 w-3" /> : null}
            {statusLabel}
          </Badge>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-5 px-5 py-6 lg:px-8">
        <button
          onClick={() => navigate('/submission')}
          className="inline-flex items-center gap-2 text-sm text-subtle-foreground-foreground transition-colors hover:text-foreground cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> Back to submission
        </button>

        {!claim && (
          <ErrorState
            inline
            title="No claim snapshot found"
            message="Process a claim first, then reopen this portal to auto-fill."
          />
        )}

        {claim && (
          <Card className="p-5 sm:p-6">
            <SectionHeader title="Claim application form" description="Fields auto-populated from extracted claim data" />

            <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={(e) => e.preventDefault()}>
              {Object.keys(form).map((key) => (
                <Input
                  key={key}
                  label={FIELD_LABELS[key] || key}
                  value={form[key]}
                  readOnly
                  placeholder="—"
                />
              ))}
            </form>
          </Card>
        )}

        {/* Status bar */}
        <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-subtle-foreground-foreground">
            {isFilling ? (
              <Loader2 className="h-4 w-4 text-brand motion-safe:animate-spin" />
            ) : (
              <CheckCircle2 className={`h-4 w-4 ${isComplete ? 'text-success' : 'text-subtle-foreground'}`} />
            )}
            {isFilling ? 'Agent is auto-filling the portal form…' : isComplete ? 'Portal form filled successfully' : 'Ready to auto-fill'}
          </div>
          {isComplete && (
            <div className="rounded-md border border-success/30 bg-success-subtle px-3 py-1.5 text-sm font-semibold text-success">
              Application #: {appNumber}
            </div>
          )}
        </Card>
      </main>
    </div>
  )
}
