import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Upload, Play, RotateCcw, FileText, File,
  CheckCircle2, Loader2, ScanLine
} from 'lucide-react'

export default function DocumentViewer({
  uploadedFile, fileInputRef, onFileChange,
  onProcess, onReset, isProcessing, isComplete, demoMode, results,
}) {
  const [drag, setDrag] = useState(false)

  const claim = results?.claimData
  const patientName = claim?.patientName || '—'
  const policyNumber = claim?.policyNumber || '—'
  const providerName = claim?.provider || '—'
  const diagnosisCode = claim?.diagnosisCode || '—'
  const cptCode = claim?.cptCode || '—'
  const totalBilled = typeof claim?.totalBilled === 'number'
    ? `$${claim.totalBilled.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '—'

  const formatIsoDate = (value) => {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '—'
    return `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}/${String(date.getFullYear()).slice(-2)}`
  }

  const dobFormatted = formatIsoDate(claim?.dob)
  const dosFormatted = formatIsoDate(claim?.dateOfService)

  const onDragOver = (e) => { e.preventDefault(); setDrag(true) }
  const onDragLeave = () => setDrag(false)
  const onDrop = (e) => {
    e.preventDefault(); setDrag(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      const dt = new DataTransfer(); dt.items.add(file)
      fileInputRef.current.files = dt.files
      onFileChange({ target: { files: [file] } })
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }} className="glass overflow-hidden">

      {/* Header */}
      <div className="flex flex-col gap-3 px-4 py-4 border-b border-border sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-violet-dim flex items-center justify-center">
            <FileText className="w-4 h-4 text-violet" />
          </div>
          <div>
            <h2 className="font-bold text-text text-sm">Document Viewer</h2>
            <p className="text-[11px] text-text-dim">
              {uploadedFile ? uploadedFile.name : demoMode ? 'Demo mode — sample claim loaded' : 'Upload a claim document'}
            </p>
          </div>
        </div>

        <div className="flex w-full flex-wrap items-center justify-end gap-2 sm:w-auto">
          {!isProcessing && !isComplete && (
            <>
              <motion.button onClick={() => fileInputRef.current?.click()}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-card-solid/60 border border-border text-sm text-text-dim hover:border-violet/30 hover:text-violet transition-all cursor-pointer">
                <Upload className="w-4 h-4" /><span className="hidden sm:inline">Upload</span>
              </motion.button>
              <motion.button onClick={onProcess}
                whileHover={{ scale: 1.06, boxShadow: '0 0 25px rgba(139,92,246,0.35)' }}
                whileTap={{ scale: 0.95 }}
                className="flex items-center gap-2 px-5 py-2 rounded-xl font-semibold text-sm text-white overflow-hidden relative cursor-pointer">
                <div className="absolute inset-0 btn-shimmer" />
                <span className="relative flex items-center gap-2"><Play className="w-4 h-4" />Process</span>
              </motion.button>
            </>
          )}
          {isProcessing && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-dim border border-violet/30 text-violet text-sm font-medium">
              <Loader2 className="w-4 h-4 animate-spin" />Processing...
            </div>
          )}
          {isComplete && (
            <motion.button onClick={onReset}
              initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-card-solid/60 border border-border text-sm text-text-dim hover:border-violet/30 hover:text-violet transition-all cursor-pointer">
              <RotateCcw className="w-4 h-4" />New Claim
            </motion.button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="relative min-h-[320px] sm:min-h-[420px]">
        {!uploadedFile && !demoMode ? (
          /* ── Dropzone ── */
          <div className={`flex flex-col items-center justify-center p-8 sm:p-14 min-h-[320px] sm:min-h-[420px] transition-all ${drag ? 'bg-violet/[0.04]' : ''}`}
            onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
            <motion.div animate={drag ? { scale: 1.12 } : { scale: 1 }}
              className={`w-20 h-20 rounded-2xl flex items-center justify-center mb-6 border-2 border-dashed transition-all ${
                drag ? 'bg-violet-dim border-violet/40' : 'bg-card-solid/50 border-border'}`}>
              <Upload className={`w-8 h-8 ${drag ? 'text-violet' : 'text-text-dim/30'}`} />
            </motion.div>
            <h3 className="text-lg font-semibold text-text mb-2 text-center">Drop your claim document here</h3>
            <p className="text-sm text-text-dim mb-5 text-center">Supports PDF, PNG, JPG, and JPEG files</p>
            <button onClick={() => fileInputRef.current?.click()}
              className="px-5 py-2.5 rounded-xl border border-violet/25 text-violet text-sm font-medium hover:bg-violet-dim transition-colors cursor-pointer">
              Browse Files
            </button>
          </div>
        ) : (
          /* ── Simulated CMS-1500 ── */
          <div className="p-4 sm:p-6 space-y-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <File className="w-4 h-4 text-violet/50" />
                <span className="text-xs font-mono text-text-dim">{uploadedFile?.name || 'CMS-1500_Claim_Form.pdf'}</span>
              </div>
              {isComplete && (
                <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-success/8 border border-success/25">
                  <CheckCircle2 className="w-3 h-3 text-success" /><span className="text-[11px] text-success font-medium">Processed</span>
                </motion.div>
              )}
            </div>

            <div className="overflow-x-auto rounded-2xl">
              <div className="bg-[#080D1B] rounded-2xl p-5 border border-white/[0.04] font-mono text-xs space-y-3 relative overflow-hidden min-w-[680px]">
                {isProcessing && <div className="scan-line absolute inset-0 z-10 pointer-events-none" />}

                <div className="border-b border-white/[0.06] pb-3 mb-3 text-center">
                  <div className="text-text-dim/30 text-[10px] tracking-[0.25em] mb-1">HEALTH INSURANCE CLAIM FORM</div>
                  <div className="text-text/50 font-bold">CMS-1500 (02/12)</div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div><div className="text-text-dim/25 text-[10px] mb-1">1. MEDICARE / MEDICAID</div><div className="text-violet/60">☑ GROUP HEALTH PLAN</div></div>
                  <div><div className="text-text-dim/25 text-[10px] mb-1">1a. INSURED'S ID NUMBER</div><div className="text-text/60">{policyNumber}</div></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><div className="text-text-dim/25 text-[10px] mb-1">2. PATIENT'S NAME</div><div className="text-text/60">{patientName}</div></div>
                  <div><div className="text-text-dim/25 text-[10px] mb-1">3. PATIENT'S BIRTH DATE</div><div className="text-text/60">{dobFormatted}</div></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-text-dim/25 text-[10px] mb-1">5. PATIENT'S ADDRESS</div>
                    <div className="text-text/60">From source document</div>
                    <div className="text-text-dim/40">Address parsing not configured</div>
                  </div>
                  <div><div className="text-text-dim/25 text-[10px] mb-1">11. INSURED'S POLICY GROUP</div><div className="text-text/60">{policyNumber !== '—' ? 'Detected from claim' : '—'}</div></div>
                </div>

                {/* Diagnosis */}
                <div className="border-t border-white/[0.06] pt-3 mt-3">
                  <div className="text-text-dim/25 text-[10px] mb-2">21. DIAGNOSIS OR NATURE OF ILLNESS</div>
                  <div className="grid grid-cols-4 gap-2">
                    <div className="bg-violet/[0.06] border border-violet/15 rounded-lg px-2.5 py-1.5">
                      <div className="text-[10px] text-violet/40">A.</div>
                      <div className="text-violet font-bold text-sm">{diagnosisCode}</div>
                    </div>
                    {['B.','C.','D.'].map(l => (
                      <div key={l} className="bg-white/[0.015] border border-white/[0.04] rounded-lg px-2.5 py-1.5">
                        <div className="text-[10px] text-text-dim/20">{l}</div>
                        <div className="text-text-dim/20">—</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Procedures */}
                <div className="border-t border-white/[0.06] pt-3 mt-3">
                  <div className="text-text-dim/25 text-[10px] mb-2">24. PROCEDURES / SERVICES</div>
                  <div className="bg-white/[0.015] rounded-xl border border-white/[0.04] overflow-hidden">
                    <div className="grid grid-cols-6 gap-1 p-2.5 text-[10px] text-text-dim/25 border-b border-white/[0.04]">
                      <span>DATE</span><span>PLACE</span><span>CPT</span><span>DIAG</span><span>CHARGES</span><span>UNITS</span>
                    </div>
                    <div className="grid grid-cols-6 gap-1 p-2.5 text-[11px]">
                      <span className="text-text/50">{dosFormatted}</span>
                      <span className="text-text/50">11</span>
                      <span className="text-cyan font-bold">{cptCode}</span>
                      <span className="text-text/50">A</span>
                      <span className="text-cyan font-bold">{totalBilled}</span>
                      <span className="text-text/50">1</span>
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="border-t border-white/[0.06] pt-3 mt-3 grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-text-dim/25 text-[10px] mb-1">33. BILLING PROVIDER</div>
                    <div className="text-text/60">{providerName}</div>
                    <div className="text-text-dim/30">NPI: From source data</div>
                  </div>
                  <div>
                    <div className="text-text-dim/25 text-[10px] mb-1">28. TOTAL CHARGE</div>
                    <div className="text-cyan font-bold text-xl">{totalBilled}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
