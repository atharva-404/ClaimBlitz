import React, { useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Building2, CheckCircle2, Circle, ClipboardCheck,
  Clock, ExternalLink, FileText, ShieldCheck,
} from 'lucide-react'
import { cn } from '../lib/utils'

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const INSURERS = [
  { id: 'aetna', name: 'Aetna', tagline: 'Enterprise claims workflow', intake: 'CMS-style claim intake' },
  { id: 'uhc', name: 'UnitedHealthcare', tagline: 'Health claims intake', intake: 'Provider claim workflow' },
  { id: 'cigna', name: 'Cigna Healthcare', tagline: 'Medical claims workflow', intake: 'Digital claim intake' },
  { id: 'bcbs', name: 'Blue Cross Blue Shield', tagline: 'Standardized medical claims', intake: 'CMS-style intake' },
]

const WORKFLOW_STEPS = [
  'Processed',
  'Risk assessed',
  'Ready for submission',
  'Select insurer',
  'Submit manually',
]
const ACTIVE_STEP = 2 // "Ready for submission"

// Preserve backward-compatible localStorage key written by useClaimAgent.
const LATEST_CLAIM_KEY = 'binaryblitz.latestClaim'

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatINR(amount) {
  if (amount == null || amount === '') return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(amount))
}

function deriveClaimId(snapshot) {
  const digits = (snapshot?.claimData?.policyNumber || '').replace(/\D/g, '')
  const tail = digits.slice(-5).padStart(5, '0') || '10482'
  return `CLM-${new Date().getFullYear()}-${tail}`
}

function formatDate(iso) {
  if (!iso) return null
  try {
    return new Date(iso).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    })
  } catch {
    return iso
  }
}

function formatTimestamp(iso) {
  if (!iso) return null
  try {
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

/** Build the claim summary rows from whatever the snapshot contains. */
function buildSummary(snap) {
  if (!snap) return []
  const d = snap.claimData || {}
  const rows = []
  const push = (label, value) => { if (value) rows.push([label, value]) }

  push('Patient', d.patientName)
  push('Claim ID', deriveClaimId(snap))
  push('Policy number', d.policyNumber)
  push('Healthcare provider', d.provider)
  if (d.diagnosisDesc || d.diagnosisCode) {
    push('Diagnosis', d.diagnosisDesc
      ? `${d.diagnosisDesc}${d.diagnosisCode ? ` (${d.diagnosisCode})` : ''}`
      : d.diagnosisCode)
  }
  if (d.cptCode) push('Procedure code', d.cptCode)
  push('Date of service', formatDate(d.dateOfService))
  if (d.totalBilled != null) push('Claim amount', formatINR(d.totalBilled))
  if (d.approvedAmount != null) push('Approved amount', formatINR(d.approvedAmount))
  if (d.patientResponsibility != null) push('Patient responsibility', formatINR(d.patientResponsibility))
  return rows
}

/** Build processing metadata from the snapshot. */
function buildMetadata(snap) {
  if (!snap) return []
  const rows = []
  const push = (label, value) => { if (value) rows.push([label, value]) }

  push('Processed', formatTimestamp(snap.savedAt))
  push('Source document', snap.sourceFileName)
  push('Risk assessment', 'Completed')
  push('Recommendation', snap.recommendation)
  return rows
}

/* ------------------------------------------------------------------ */
/*  Small components                                                   */
/* ------------------------------------------------------------------ */

function WorkflowIndicator({ hasSnapshot }) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-1">
      {WORKFLOW_STEPS.map((label, i) => {
        const done = hasSnapshot && i < ACTIVE_STEP
        const active = hasSnapshot && i === ACTIVE_STEP
        const future = !hasSnapshot || i > ACTIVE_STEP
        return (
          <React.Fragment key={label}>
            {i > 0 && (
              <span
                className={cn(
                  'hidden h-px w-5 shrink-0 sm:block',
                  done ? 'bg-success' : active ? 'bg-primary' : 'bg-border',
                )}
              />
            )}
            <span
              className={cn(
                'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold whitespace-nowrap transition-colors',
                done && 'bg-success-subtle text-success',
                active && 'bg-primary-subtle text-accent-foreground ring-1 ring-primary/20',
                future && 'bg-surface-muted text-subtle-foreground',
              )}
            >
              {done ? <CheckCircle2 className="h-3 w-3" /> : active ? <Clock className="h-3 w-3" /> : <Circle className="h-3 w-3" />}
              {label}
            </span>
          </React.Fragment>
        )
      })}
    </div>
  )
}

function InsurerCard({ insurer, ready, onOpen }) {
  return (
    <div className="panel flex flex-col p-5 transition-colors hover:border-primary-border">
      <div className="flex items-start justify-between">
        <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary-subtle">
          <Building2 className="h-5 w-5 text-primary" />
        </span>
        <span
          className={cn(
            'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
            ready ? 'bg-success-subtle text-success' : 'bg-surface-muted text-muted-foreground',
          )}
        >
          {ready ? 'Ready' : 'No claim'}
        </span>
      </div>

      <h3 className="mt-4 text-base font-semibold text-foreground">{insurer.name}</h3>
      <p className="mt-0.5 text-sm text-muted-foreground">{insurer.tagline}</p>

      <dl className="mt-3 space-y-1 text-xs text-subtle-foreground">
        <div className="flex items-center gap-1.5">
          <FileText className="h-3 w-3" />
          <span>{insurer.intake}</span>
        </div>
      </dl>

      <p className="mt-3 flex-1 text-[11px] leading-relaxed text-subtle-foreground">
        Opens a simulated insurer portal and auto-fills the processed claim data. You submit manually from within the portal.
      </p>

      <button
        disabled={!ready}
        onClick={onOpen}
        className="mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        <ExternalLink className="h-4 w-4" />
        Open &amp; auto-fill
      </button>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function SubmissionPage() {
  const navigate = useNavigate()

  const claimSnapshot = useMemo(() => {
    try {
      const raw = localStorage.getItem(LATEST_CLAIM_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }, [])

  const openPortal = (insurerId) => {
    const url = `/portal/${insurerId}?autofill=1`
    const popup = window.open(url, '_blank', 'noopener,noreferrer')
    if (!popup) navigate(url)
  }

  const summary = buildSummary(claimSnapshot)
  const metadata = buildMetadata(claimSnapshot)

  const riskLabel = claimSnapshot?.riskLabel
  const riskPct = Math.round((claimSnapshot?.riskScore || 0) * 100)
  const riskTone =
    riskLabel === 'HIGH' ? 'bg-destructive/10 text-destructive'
      : riskLabel === 'MEDIUM' ? 'bg-warning-subtle text-warning'
      : 'bg-success-subtle text-success'

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center gap-3 px-5">
          <button
            onClick={() => navigate('/dashboard')}
            aria-label="Back to dashboard"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <Link
            to="/"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-[13px] font-bold text-white"
            aria-label="ClaimBitz home"
          >
            C
          </Link>
          <div className="min-w-0">
            <h1 className="text-[15px] font-semibold leading-tight tracking-tight text-foreground">
              Claim submission
            </h1>
            <p className="hidden text-xs text-muted-foreground sm:block">
              Route the processed claim to an insurer portal
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1240px] space-y-6 px-5 py-6">

        {/* Workflow indicator */}
        <WorkflowIndicator hasSnapshot={!!claimSnapshot} />

        {/* Claim summary */}
        <section className="panel overflow-hidden">
          <div className="flex items-start gap-3 border-b border-border px-5 py-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-subtle">
              <ClipboardCheck className="h-[18px] w-[18px] text-primary" />
            </span>
            <div className="min-w-0">
              <h2 className="text-[15px] font-semibold text-foreground">Claim ready for submission</h2>
              <p className="mt-0.5 text-[13px] text-muted-foreground">
                Extracted from the most recently processed document
              </p>
            </div>
            {claimSnapshot && (
              <span className={cn('ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold', riskTone)}>
                <ShieldCheck className="h-3 w-3" />
                {riskPct}% · {riskLabel}
              </span>
            )}
          </div>

          {!claimSnapshot ? (
            <div className="flex items-start gap-3 px-5 py-5" role="alert">
              <div className="rounded-md border border-warning/30 bg-warning-subtle px-4 py-3 w-full">
                <p className="text-sm font-semibold text-warning">No processed claim found</p>
                <p className="mt-0.5 text-sm text-warning/90">
                  Process a document on the dashboard first, then return here to submit.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid lg:grid-cols-[1.4fr_1fr] divide-y lg:divide-y-0 lg:divide-x divide-border">
              {/* Left: claim fields */}
              <dl className="grid gap-x-8 px-5 py-4 sm:grid-cols-2">
                {summary.map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between gap-4 border-b border-border py-2.5 last:border-b-0">
                    <dt className="text-[13px] text-muted-foreground">{label}</dt>
                    <dd className="text-right text-[13px] font-medium text-foreground">{value}</dd>
                  </div>
                ))}
              </dl>

              {/* Right: processing metadata */}
              <div className="px-5 py-4">
                <p className="eyebrow mb-2">Processing details</p>
                <dl className="space-y-2">
                  {metadata.map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between gap-4">
                      <dt className="text-[12.5px] text-muted-foreground">{label}</dt>
                      <dd className="text-[12.5px] font-medium text-foreground">{value}</dd>
                    </div>
                  ))}
                </dl>

                {claimSnapshot.riskReasons && claimSnapshot.riskReasons.length > 0 && (
                  <div className="mt-4 border-t border-border pt-3">
                    <p className="eyebrow mb-1.5">Risk factors</p>
                    <ul className="space-y-1">
                      {claimSnapshot.riskReasons.slice(0, 3).map((r, i) => (
                        <li key={i} className="text-[12px] leading-relaxed text-subtle-foreground">
                          · {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Insurer selection */}
        <section>
          <p className="eyebrow mb-3">Select insurer portal</p>
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {INSURERS.map((insurer) => (
              <InsurerCard
                key={insurer.id}
                insurer={insurer}
                ready={!!claimSnapshot}
                onOpen={() => openPortal(insurer.id)}
              />
            ))}
          </div>
        </section>

        {/* Transparency notice */}
        <footer className="space-y-2 border-t border-border pt-4">
          <p className="text-xs leading-relaxed text-subtle-foreground">
            ClaimBitz prepares and pre-fills claim information for submission.
            Final submission and insurer decisions remain under human control.
          </p>
          <p className="text-[11px] text-subtle-foreground/70">
            Demo integration — insurer portals shown for workflow demonstration. No live insurer submission is performed.
          </p>
        </footer>
      </main>
    </div>
  )
}
