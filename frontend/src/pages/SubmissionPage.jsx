import React, { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ExternalLink, ClipboardCheck } from 'lucide-react'

const INSURERS = [
  { id: 'aetna', name: 'Aetna Claim Portal Clone', tagline: 'Enterprise provider workflow' },
  { id: 'uhc', name: 'UnitedHealthcare Portal Clone', tagline: 'Fast adjudication pipeline' },
  { id: 'bcbs', name: 'Blue Cross Blue Shield Clone', tagline: 'Standardized CMS-style intake' },
]

export default function SubmissionPage() {
  const navigate = useNavigate()

  const claimSnapshot = useMemo(() => {
    try {
      const raw = localStorage.getItem('binaryblitz.latestClaim')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }, [])

  const openPortal = (insurerId) => {
    const url = `/portal/${insurerId}?autofill=1`
    const popup = window.open(url, '_blank', 'noopener,noreferrer')
    if (!popup) {
      navigate(url)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-base grid-pattern p-5 lg:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <button onClick={() => navigate('/dashboard')} className="flex items-center gap-2 text-sm text-text-dim hover:text-text cursor-pointer">
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </button>
        </div>

        <div className="glass p-5">
          <h1 className="text-xl font-bold text-text">Claim Submission Hub</h1>
          <p className="text-sm text-text-dim mt-1">
            Choose insurer platform clone. The agent will open it in a subtab and auto-fill from extracted PDF data.
          </p>
          {!claimSnapshot && (
            <div className="mt-4 text-xs text-warning bg-warning/10 border border-warning/20 rounded-lg p-3">
              No processed claim found in local storage. Process a PDF first, then return here.
            </div>
          )}

          {claimSnapshot && (
            <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
              <div className="rounded-lg border border-border p-3 bg-card-solid/50">
                <div className="text-text-dim">Patient</div>
                <div className="text-text font-semibold">{claimSnapshot.claimData?.patientName}</div>
              </div>
              <div className="rounded-lg border border-border p-3 bg-card-solid/50">
                <div className="text-text-dim">Policy</div>
                <div className="text-text font-semibold">{claimSnapshot.claimData?.policyNumber}</div>
              </div>
              <div className="rounded-lg border border-border p-3 bg-card-solid/50">
                <div className="text-text-dim">Risk</div>
                <div className="text-text font-semibold">{Math.round((claimSnapshot.riskScore || 0) * 100)}% ({claimSnapshot.riskLabel})</div>
              </div>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {INSURERS.map((insurer) => (
            <div key={insurer.id} className="glass p-5 space-y-4">
              <div>
                <h2 className="text-base font-bold text-text">{insurer.name}</h2>
                <p className="text-xs text-text-dim">{insurer.tagline}</p>
              </div>

              <div className="text-xs text-text-dim rounded-lg bg-card-solid/50 border border-border p-3">
                Agentic AI action:
                <div className="mt-1 text-text">Open portal subtab → map extracted fields → auto-fill form → generate application number.</div>
              </div>

              <button
                disabled={!claimSnapshot}
                onClick={() => openPortal(insurer.id)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-violet-dim border border-violet/30 text-violet text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                <ExternalLink className="w-4 h-4" /> Open & Auto Fill
              </button>
            </div>
          ))}
        </div>

        <div className="glass p-4 flex items-center gap-3">
          <ClipboardCheck className="w-5 h-5 text-success" />
          <p className="text-sm text-text-dim">Submission data source is local snapshot saved from the latest processed PDF.</p>
        </div>
      </div>
    </motion.div>
  )
}
