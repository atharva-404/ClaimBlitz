import React, { useState } from 'react'
import {
  Upload, Play, RotateCcw, FileText, CheckCircle2,
} from 'lucide-react'
import { Card, Button, Badge, SectionHeader, Spinner } from './ui'

/* A single labelled field in the claim preview. */
function Field({ label, value, accent = false, mono = false }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-subtle-foreground">{label}</div>
      <div
        className={`mt-0.5 text-sm ${mono ? 'font-mono' : ''} ${
          accent ? 'font-semibold text-brand' : 'font-medium text-foreground'
        }`}
      >
        {value}
      </div>
    </div>
  )
}

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
      if (fileInputRef.current) fileInputRef.current.files = dt.files
      onFileChange({ target: { files: [file] } })
    }
  }

  const hasDocument = uploadedFile || demoMode

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="flex flex-col gap-3 border-b border-default px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <SectionHeader
          icon={FileText}
          title="Claim Document"
          description={
            uploadedFile ? uploadedFile.name : demoMode ? 'Demo mode — sample claim loaded' : 'Upload a claim document to begin'
          }
        />

        <div className="flex w-full flex-wrap items-center justify-end gap-2 sm:w-auto">
          {!isProcessing && !isComplete && (
            <>
              <Button variant="secondary" size="md" onClick={() => fileInputRef.current?.click()}>
                <Upload className="h-4 w-4" />
                <span className="hidden sm:inline">Upload</span>
              </Button>
              <Button variant="primary" size="md" onClick={onProcess}>
                <Play className="h-4 w-4" />
                Process claim
              </Button>
            </>
          )}
          {isProcessing && (
            <div className="inline-flex h-10 items-center gap-2 rounded-md border border-default bg-subtle px-4 text-sm font-medium text-subtle-foreground-foreground">
              <Spinner className="h-4 w-4 text-brand" />
              Processing…
            </div>
          )}
          {isComplete && (
            <Button variant="secondary" size="md" onClick={onReset}>
              <RotateCcw className="h-4 w-4" />
              New claim
            </Button>
          )}
        </div>
      </div>

      {/* Body */}
      <div>
        {!hasDocument ? (
          /* ── Dropzone ── */
          <div
            className={`flex min-h-[320px] flex-col items-center justify-center p-8 text-center transition-colors sm:min-h-[420px] ${
              drag ? 'bg-brand-subtle' : ''
            }`}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
          >
            <div
              className={`mb-5 flex h-16 w-16 items-center justify-center rounded-lg border-2 border-dashed transition-colors ${
                drag ? 'border-brand bg-brand-subtle' : 'border-default bg-subtle'
              }`}
            >
              <Upload className={`h-7 w-7 ${drag ? 'text-brand' : 'text-subtle-foreground'}`} />
            </div>
            <h3 className="text-base font-semibold text-foreground">Drop your claim document here</h3>
            <p className="mt-1 text-sm text-subtle-foreground-foreground">Supports PDF, PNG, JPG and JPEG files</p>
            <Button variant="secondary" size="md" className="mt-5" onClick={() => fileInputRef.current?.click()}>
              Browse files
            </Button>
          </div>
        ) : (
          /* ── Claim preview (CMS-1500) ── */
          <div className="p-4 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-subtle-foreground-foreground">
                <FileText className="h-4 w-4 text-subtle-foreground" />
                <span className="font-mono text-xs">{uploadedFile?.name || 'CMS-1500_Claim_Form.pdf'}</span>
              </div>
              {isComplete && (
                <Badge variant="success">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Processed
                </Badge>
              )}
            </div>

            {/* Document surface — white, subtle border, responsive layout */}
            <div className="rounded-lg border border-default bg-surface">
              {/* Document masthead */}
              <div className="border-b border-default px-4 py-3 text-center sm:px-6">
                <div className="text-[11px] font-medium uppercase tracking-[0.2em] text-subtle-foreground">
                  Health Insurance Claim Form
                </div>
                <div className="mt-0.5 text-sm font-semibold text-foreground">CMS-1500 (02/12)</div>
              </div>

              {/* Patient / insured */}
              <div className="grid gap-4 border-b border-default px-4 py-4 sm:grid-cols-2 sm:px-6">
                <Field label="2. Patient's name" value={patientName} />
                <Field label="1a. Insured's ID number" value={policyNumber} mono />
                <Field label="3. Patient's birth date" value={dobFormatted} mono />
                <Field label="11. Insured's policy group" value={policyNumber !== '—' ? 'Detected from claim' : '—'} />
              </div>

              {/* Diagnosis */}
              <div className="border-b border-default px-4 py-4 sm:px-6">
                <div className="mb-2 text-xs font-medium uppercase tracking-wide text-subtle-foreground">
                  21. Diagnosis or nature of illness
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <div className="rounded-md border border-brand/30 bg-brand-subtle px-3 py-2">
                    <div className="text-[11px] text-brand/70">A.</div>
                    <div className="text-sm font-semibold text-brand">{diagnosisCode}</div>
                  </div>
                  {['B.', 'C.', 'D.'].map((l) => (
                    <div key={l} className="rounded-md border border-default bg-subtle px-3 py-2">
                      <div className="text-[11px] text-subtle-foreground">{l}</div>
                      <div className="text-sm text-subtle-foreground">—</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Procedures — responsive: table on sm+, stacked on mobile */}
              <div className="border-b border-default px-4 py-4 sm:px-6">
                <div className="mb-2 text-xs font-medium uppercase tracking-wide text-subtle-foreground">
                  24. Procedures / services
                </div>

                {/* Mobile stacked view */}
                <div className="grid grid-cols-2 gap-3 sm:hidden">
                  <Field label="Date" value={dosFormatted} mono />
                  <Field label="Place" value="11" mono />
                  <Field label="CPT" value={cptCode} accent mono />
                  <Field label="Diagnosis" value="A" mono />
                  <Field label="Charges" value={totalBilled} accent mono />
                  <Field label="Units" value="1" mono />
                </div>

                {/* Table view (sm and up) */}
                <div className="hidden overflow-hidden rounded-md border border-default sm:block">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-default bg-subtle text-left text-xs uppercase tracking-wide text-subtle-foreground">
                        <th className="px-3 py-2 font-medium">Date</th>
                        <th className="px-3 py-2 font-medium">Place</th>
                        <th className="px-3 py-2 font-medium">CPT</th>
                        <th className="px-3 py-2 font-medium">Diag</th>
                        <th className="px-3 py-2 font-medium">Charges</th>
                        <th className="px-3 py-2 font-medium">Units</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="text-foreground">
                        <td className="px-3 py-2.5 font-mono">{dosFormatted}</td>
                        <td className="px-3 py-2.5 font-mono">11</td>
                        <td className="px-3 py-2.5 font-mono font-semibold text-brand">{cptCode}</td>
                        <td className="px-3 py-2.5 font-mono">A</td>
                        <td className="px-3 py-2.5 font-mono font-semibold">{totalBilled}</td>
                        <td className="px-3 py-2.5 font-mono">1</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Footer */}
              <div className="grid gap-4 px-4 py-4 sm:grid-cols-2 sm:px-6">
                <Field label="33. Billing provider" value={providerName} />
                <div className="sm:text-right">
                  <div className="text-xs font-medium uppercase tracking-wide text-subtle-foreground">28. Total charge</div>
                  <div className="mt-0.5 text-xl font-semibold text-foreground">{totalBilled}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}
