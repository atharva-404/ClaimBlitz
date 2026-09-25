import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ExternalLink, ClipboardCheck, Building2 } from 'lucide-react'
import { Card, Button, Badge, SectionHeader, DescriptionList, ErrorState } from '../components/ui'

const INSURERS = [
  { id: 'aetna', name: 'Aetna Claim Portal', tagline: 'Enterprise provider workflow' },
  { id: 'uhc', name: 'UnitedHealthcare Portal', tagline: 'Fast adjudication pipeline' },
  { id: 'bcbs', name: 'Blue Cross Blue Shield', tagline: 'Standardized CMS-style intake' },
]

// Preserve backward-compatible localStorage key written by useClaimAgent.
const LATEST_CLAIM_KEY = 'binaryblitz.latestClaim'

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

  return (
    <div className="min-h-screen bg-canvas">
      {/* Header */}
      <header className="border-b border-default bg-surface">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-5 py-4 lg:px-8">
          <button
            onClick={() => navigate('/dashboard')}
            aria-label="Back to dashboard"
            className="rounded-md p-2 text-secondary transition-colors hover:bg-subtle hover:text-primary cursor-pointer"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-base font-semibold text-primary">Claim submission</h1>
            <p className="text-xs text-muted">Route the processed claim to an insurer portal</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-5 py-6 lg:px-8">
        {/* Claim snapshot */}
        <Card className="p-5">
          <SectionHeader
            icon={ClipboardCheck}
            title="Claim ready for submission"
            description="Extracted from the most recently processed document"
          />
          {!claimSnapshot ? (
            <ErrorState
              inline
              title="No processed claim found"
              message="Process a document on the dashboard first, then return here to submit."
              className="mt-4"
            />
          ) : (
            <DescriptionList
              columns={2}
              className="mt-4"
              items={[
                { label: 'Patient', value: claimSnapshot.claimData?.patientName || '—' },
                { label: 'Policy number', value: claimSnapshot.claimData?.policyNumber || '—' },
                { label: 'Provider', value: claimSnapshot.claimData?.provider || '—' },
                {
                  label: 'Risk',
                  value: (
                    <Badge
                      variant={
                        claimSnapshot.riskLabel === 'HIGH' ? 'error' :
                        claimSnapshot.riskLabel === 'MEDIUM' ? 'warning' : 'success'
                      }
                    >
                      {Math.round((claimSnapshot.riskScore || 0) * 100)}% · {claimSnapshot.riskLabel}
                    </Badge>
                  ),
                },
              ]}
            />
          )}
        </Card>

        {/* Insurer selection */}
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Select insurer portal</h2>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {INSURERS.map((insurer) => (
              <Card key={insurer.id} variant="interactive" className="flex flex-col p-5">
                <div className="flex items-start justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-brand-subtle">
                    <Building2 className="h-5 w-5 text-brand" />
                  </div>
                  <Badge variant={claimSnapshot ? 'success' : 'neutral'}>
                    {claimSnapshot ? 'Ready' : 'No claim'}
                  </Badge>
                </div>
                <h3 className="mt-4 text-base font-semibold text-primary">{insurer.name}</h3>
                <p className="mt-0.5 text-sm text-secondary">{insurer.tagline}</p>
                <p className="mt-3 flex-1 text-xs leading-relaxed text-muted">
                  Opens the portal, maps extracted fields, auto-fills the form and generates an application number.
                </p>
                <Button
                  variant="primary"
                  size="md"
                  className="mt-4 w-full"
                  disabled={!claimSnapshot}
                  onClick={() => openPortal(insurer.id)}
                >
                  <ExternalLink className="h-4 w-4" />
                  Open &amp; auto-fill
                </Button>
              </Card>
            ))}
          </div>
        </div>

        <p className="text-xs text-muted">
          Submission data comes from the local snapshot saved after the latest processed document.
        </p>
      </main>
    </div>
  )
}
