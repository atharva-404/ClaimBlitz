import React, { useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ShieldCheck } from 'lucide-react'
import { useClaimAgent } from '../hooks/useClaimAgent'
import RiskMeter from '../components/RiskMeter'
import AgentStepper from '../components/AgentStepper'
import TerminalWindow from '../components/TerminalWindow'
import DocumentViewer from '../components/DocumentViewer'
import OutputSection from '../components/OutputSection'
import { Button, StatusDot, ErrorState } from '../components/ui'

function statusMeta({ isProcessing, isComplete }) {
  if (isProcessing) return { variant: 'warning', label: 'Processing', pulse: true }
  if (isComplete) return { variant: 'success', label: 'Complete', pulse: false }
  return { variant: 'neutral', label: 'Ready', pulse: false }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const {
    agents, currentStep, isProcessing, isComplete,
    results, riskScore, demoMode, setDemoMode,
    terminalLogs, uploadedFile, errorMessage, handleUpload, process, reset,
  } = useClaimAgent()
  const fileInputRef = useRef(null)

  const onFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
  }

  const status = statusMeta({ isProcessing, isComplete })

  return (
    <div className="min-h-screen w-full bg-canvas">
      {/* ── Top Bar ── */}
      <header className="sticky top-0 z-50 border-b border-default bg-surface">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={() => navigate('/')}
              aria-label="Back to home"
              className="rounded-md p-2 text-secondary transition-colors hover:bg-subtle hover:text-primary cursor-pointer"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-semibold leading-tight text-primary">ClaimBitz Console</h1>
              <p className="text-xs text-muted">Collaborative claim analysis pipeline</p>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            {/* Demo toggle */}
            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-default bg-surface px-3 py-2">
              <span className="text-xs font-medium text-secondary">Demo mode</span>
              <button
                type="button"
                role="switch"
                aria-checked={demoMode}
                aria-label="Toggle demo mode"
                onClick={() => setDemoMode(!demoMode)}
                className={`relative h-5 w-9 rounded-full transition-colors cursor-pointer ${
                  demoMode ? 'bg-brand' : 'bg-default'
                }`}
              >
                <span
                  className="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-[0_1px_2px_rgba(16,24,40,0.06)] transition-all"
                  style={{ left: demoMode ? '18px' : '2px' }}
                />
              </button>
            </label>

            {/* Status pill */}
            <div className="flex items-center gap-2 rounded-md border border-default bg-surface px-3 py-2">
              <StatusDot variant={status.variant} pulse={status.pulse} />
              <span className="hidden text-xs font-medium text-secondary sm:inline">{status.label}</span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="mx-auto w-full max-w-[1600px] p-4 lg:p-6">
        {/* Error banner */}
        {errorMessage && (
          <ErrorState
            inline
            title="Claim processing failed"
            message={errorMessage}
            className="mb-6"
          />
        )}

        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-12">
          {/* LEFT COLUMN */}
          <div className="min-w-0 space-y-6 xl:col-span-8 2xl:col-span-9">
            <DocumentViewer
              uploadedFile={uploadedFile}
              fileInputRef={fileInputRef}
              onFileChange={onFileChange}
              onProcess={process}
              onReset={reset}
              isProcessing={isProcessing}
              isComplete={isComplete}
              demoMode={demoMode}
              results={results}
            />

            <AnimatePresence>
              {(isProcessing || isComplete) && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 12 }}
                  transition={{ duration: 0.2 }}
                  className="grid gap-6 md:grid-cols-2"
                >
                  <RiskMeter score={riskScore} isProcessing={isProcessing} results={results} />
                  {isComplete && results && <OutputSection results={results} />}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* RIGHT COLUMN */}
          <div className="space-y-6 xl:col-span-4 2xl:col-span-3 xl:sticky xl:top-24 self-start">
            <AgentStepper agents={agents} currentStep={currentStep} demoMode={demoMode} />
            <TerminalWindow logs={terminalLogs} isProcessing={isProcessing} />
          </div>
        </div>
      </main>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={onFileChange}
        className="hidden"
      />
    </div>
  )
}
