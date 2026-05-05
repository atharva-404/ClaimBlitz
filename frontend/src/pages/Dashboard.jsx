import React, { useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Zap, ToggleLeft, ToggleRight
} from 'lucide-react'
import { useClaimAgent } from '../hooks/useClaimAgent'
import RiskMeter from '../components/RiskMeter'
import AgentStepper from '../components/AgentStepper'
import TerminalWindow from '../components/TerminalWindow'
import DocumentViewer from '../components/DocumentViewer'
import OutputSection from '../components/OutputSection'

export default function Dashboard() {
  const navigate = useNavigate()
  const {
    agents, currentStep, isProcessing, isComplete,
    results, riskScore, demoMode, setDemoMode,
    terminalLogs, uploadedFile, handleUpload, process, reset,
  } = useClaimAgent()
  const fileInputRef = useRef(null)

  const onFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }} className="min-h-screen w-full bg-base grid-pattern overflow-x-clip">

      {/* ── Top Bar ── */}
      <header className="sticky top-0 z-50 px-4 lg:px-6 py-3 border-b border-border bg-base/80 backdrop-blur-2xl">
        <div className="max-w-[1600px] mx-auto flex flex-wrap items-center justify-between gap-3">
          {/* Left */}
          <div className="flex min-w-0 items-center gap-3">
            <motion.button onClick={() => navigate('/')} whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
              className="p-2 rounded-xl hover:bg-card-solid transition-colors cursor-pointer">
              <ArrowLeft className="w-5 h-5 text-text-muted" />
            </motion.button>
            <div className="w-9 h-9 rounded-xl bg-violet-dim flex items-center justify-center">
              <Zap className="w-5 h-5 text-violet" />
            </div>
            <div className="hidden sm:block">
              <h1 className="font-bold text-text text-sm leading-tight">Binary Blitz Dashboard</h1>
              <p className="text-[11px] text-text-dim">Autonomous Claim Processing Pipeline</p>
            </div>
          </div>

          {/* Right */}
          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            {/* Demo toggle */}
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-card-solid/60 border border-border">
              <span className="text-[11px] text-text-dim font-medium hidden sm:inline">Demo</span>
              <motion.button onClick={() => setDemoMode(!demoMode)} whileTap={{ scale: 0.85 }} className="cursor-pointer">
                {demoMode
                  ? <ToggleRight className="w-7 h-7 text-violet" />
                  : <ToggleLeft className="w-7 h-7 text-text-dim" />}
              </motion.button>
              {demoMode && (
                <motion.span initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: 1 }}
                  className="text-[9px] px-1.5 py-0.5 rounded-md bg-violet-dim text-violet font-bold hidden sm:inline">ON</motion.span>
              )}
            </div>

            {/* Status pill */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border ${
              isProcessing ? 'border-warning/40 bg-warning/5' :
              isComplete ? 'border-success/40 bg-success/5' :
              'border-border bg-card-solid/60'}`}>
              <div className={`w-2 h-2 rounded-full ${
                isProcessing ? 'bg-warning animate-pulse' :
                isComplete ? 'bg-success' : 'bg-text-dim/40'}`} />
              <span className="text-[11px] font-semibold text-text-dim hidden sm:inline">
                {isProcessing ? 'Processing...' : isComplete ? 'Complete' : 'Ready'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Grid ── */}
      <main className="max-w-[1600px] mx-auto w-full p-4 lg:p-6">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">

          {/* ── LEFT COLUMN ── */}
          <div className="space-y-6 min-w-0 xl:col-span-8 2xl:col-span-9">
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

            {/* Risk + Output row */}
            <AnimatePresence>
              {(isProcessing || isComplete) && (
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 30 }}
                  transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                  className="grid md:grid-cols-2 gap-6"
                >
                  <RiskMeter score={riskScore} isProcessing={isProcessing} results={results} />
                  {isComplete && results && <OutputSection results={results} />}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ── RIGHT COLUMN ── */}
          <div className="space-y-6 xl:col-span-4 2xl:col-span-3 xl:sticky xl:top-24 self-start">
            <AgentStepper agents={agents} currentStep={currentStep} />
            <TerminalWindow logs={terminalLogs} isProcessing={isProcessing} />
          </div>
        </div>
      </main>

      {/* Hidden file input */}
      <input ref={fileInputRef} type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={onFileChange} className="hidden" />
    </motion.div>
  )
}
