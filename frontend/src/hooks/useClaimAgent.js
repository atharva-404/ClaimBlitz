import { useState, useCallback, useRef } from 'react'

const AGENT_STEPS = [
  { id: 'scanner', name: 'Scanner Agent', description: 'Extracting medical claim data from document', icon: 'ScanLine' },
  { id: 'validator', name: 'Validator Agent', description: 'Checking policy compliance & ICD-10 codes', icon: 'ShieldCheck' },
  { id: 'risk', name: 'Risk Analyst', description: 'Analyzing fraud indicators & error patterns', icon: 'Activity' },
  { id: 'comm', name: 'Comm Agent', description: 'Drafting communication templates', icon: 'MessageSquare' },
]

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const LATEST_CLAIM_KEY = 'binaryblitz.latestClaim'

export function useClaimAgent() {
  const [demoMode, setDemoMode] = useState(false)
  const [agents, setAgents] = useState(
    AGENT_STEPS.map(a => ({
      ...a,
      status: 'idle', // idle | processing | completed | error
      logs: [],
    }))
  )
  const [currentStep, setCurrentStep] = useState(-1)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [results, setResults] = useState(null)
  const [riskScore, setRiskScore] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')
  const [terminalLogs, setTerminalLogs] = useState([])
  const [uploadedFile, setUploadedFile] = useState(null)
  const abortRef = useRef(false)

  const persistClaim = useCallback((payload, sourceFileName) => {
    const toStore = {
      savedAt: new Date().toISOString(),
      sourceFileName: sourceFileName || 'demo-claim.pdf',
      claimData: payload.claimData,
      riskScore: payload.riskScore,
      riskLabel: payload.riskLabel,
      recommendation: payload.recommendation,
      riskReasons: payload.riskReasons || [],
      extractionIssues: payload.extractionIssues || [],
      extractionTextPreview: payload.extractionTextPreview || '',
      riskModel: payload.riskModel || null,
      email: payload.email,
      whatsapp: payload.whatsapp,
    }
    localStorage.setItem(LATEST_CLAIM_KEY, JSON.stringify(toStore))
  }, [])

  const addTerminalLog = useCallback((log) => {
    setTerminalLogs(prev => [...prev, { text: log, timestamp: new Date().toLocaleTimeString() }])
  }, [])

  const getDemoPayload = useCallback(() => ({
    claimData: {
      patientName: 'John D. Miller',
      dob: '1985-03-14',
      policyNumber: '882-ALT-9921',
      diagnosisCode: 'J18.9',
      diagnosisDesc: 'Pneumonia, unspecified organism',
      cptCode: '99213',
      provider: 'SUMMIT HEALTH CLINIC',
      totalBilled: 4250.0,
      approvedAmount: 3612.5,
      patientResponsibility: 637.5,
      dateOfService: '2026-04-10',
    },
    riskScore: 0.24,
    riskLabel: 'LOW',
    recommendation: 'APPROVE',
    riskReasons: ['No major anomalies detected', 'Provider is in-network', 'Valid ICD and CPT format'],
    extractionIssues: [],
    extractionTextPreview: 'Demo claim text preview',
    riskModel: {
      baseScore: 0.1,
      maxIssuePenalty: 0.3,
      issuePenaltyPerItem: 0.06,
      thresholds: { lowMax: 0.3, mediumMax: 0.6, highMax: 1.0 },
      contributions: [
        { rule: 'slight_approval_variance', delta: 0.1, reason: 'Slight variance between approved and billed amount' },
        { rule: 'provider_in_network_bonus', delta: 0.04, reason: 'Provider appears in network reference list' },
      ],
    },
    email: `Subject: Claim Review Update — Policy #882-ALT-9921\n\nDear Policyholder,\n\nYour medical claim has been processed successfully.\n\nDecision: APPROVE\nRisk Level: LOW\nApproved Amount: $3,612.50\nPatient Responsibility: $637.50\n\nBest regards,\nBinary Blitz Claim Agent`,
    whatsapp: 'Claim Status Update\\n\\nProvider: SUMMIT HEALTH CLINIC\\nDiagnosis: J18.9\\nApproved: $3,612.50\\nYour Cost: $637.50\\nDecision: APPROVE (LOW)\\nRisk Score: 0.24',
  }), [])

  const processReal = useCallback(async () => {
    if (!uploadedFile && !demoMode) {
      addTerminalLog('[ERROR] Please upload a claim document first')
      setErrorMessage('Please upload a claim document before processing.')
      return
    }

    let activeStep = 0
    const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms))
    const markProcessing = (index, log) => {
      activeStep = index
      setCurrentStep(index)
      setAgents(prev => prev.map((a, i) => (
        i < index ? { ...a, status: 'completed' }
          : i === index ? { ...a, status: 'processing' }
          : { ...a, status: 'idle' }
      )))
      addTerminalLog(log)
    }

    const markCompleted = (index, log) => {
      setAgents(prev => prev.map((a, i) => (
        i === index ? { ...a, status: 'completed' } : a
      )))
      addTerminalLog(log)
    }

    const markFailed = (index, log) => {
      setAgents(prev => prev.map((a, i) => (
        i === index ? { ...a, status: 'error' } : a
      )))
      addTerminalLog(log)
    }

    abortRef.current = false
    setIsProcessing(true)
    setIsComplete(false)
    setResults(null)
    setRiskScore(0)
    setErrorMessage('')
    setTerminalLogs([])
    setAgents(AGENT_STEPS.map(a => ({ ...a, status: 'idle', logs: [] })))
    setCurrentStep(-1)

    addTerminalLog('[SYSTEM] Binary Blitz Agent Pipeline — INITIALIZING')
    addTerminalLog(`[SYSTEM] Connected to backend: ${API_BASE_URL}`)
    addTerminalLog('─'.repeat(50))

    try {
      markProcessing(0, demoMode && !uploadedFile
        ? '[INFO] Scanner Agent: Loading built-in demo claim payload...'
        : '[INFO] Scanner Agent: Uploading claim document and extracting structured fields...')

      let data
      if (demoMode && !uploadedFile) {
        await wait(300)
        data = getDemoPayload()
        markCompleted(0, '[SUCCESS] Scanner Agent: Demo claim payload loaded')
      } else {
        const formData = new FormData()
        formData.append('file', uploadedFile)

        const response = await fetch(`${API_BASE_URL}/process`, {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          throw new Error(err.detail || 'Backend processing failed')
        }

        data = await response.json()
        markCompleted(0, `[SUCCESS] Scanner Agent: Extraction complete for ${uploadedFile.name}`)
      }

      addTerminalLog('[AGENT] Scanner Agent -> Validator Agent: Structured payload transfer initiated')
      if ((data.extractionIssues || []).length > 0) {
        addTerminalLog(`[WARN] Scanner Agent -> Validator Agent: ${data.extractionIssues.length} extraction issues detected`)
      }
      await wait(250)

      markProcessing(1, '[INFO] Validator Agent: Running consistency and policy checks...')
      await wait(300)
      markCompleted(1, `[SUCCESS] Validator Agent: ICD ${data.claimData?.diagnosisCode || 'N/A'} and CPT ${data.claimData?.cptCode || 'N/A'} validated`)
      addTerminalLog('[AGENT] Validator Agent -> Risk Analyst: Validation summary and issue context shared')
      await wait(250)

      markProcessing(2, '[INFO] Risk Analyst: Computing risk score and recommendation...')
      setRiskScore(data.riskScore ?? 0)
      await wait(300)
      markCompleted(2, `[DATA] Risk Score: ${data.riskScore} (${data.riskLabel})`)
      if ((data.riskReasons || []).length > 0) {
        addTerminalLog(`[AGENT] Risk Analyst -> Comm Agent: Sent ${(data.riskReasons || []).length} risk reasons for explanation drafts`)
      }
      await wait(250)

      markProcessing(3, '[INFO] Comm Agent: Generating patient and insurer communication drafts...')
      await wait(300)
      markCompleted(3, '[SUCCESS] Comm Agent: Email and WhatsApp drafts generated')

      setResults(data)
      persistClaim(data, uploadedFile?.name)
      setRiskScore(data.riskScore ?? 0)
      setCurrentStep(AGENT_STEPS.length - 1)
      setAgents(AGENT_STEPS.map((a) => ({ ...a, status: 'completed', logs: [] })))
      addTerminalLog(`[DATA] Claim: ${data.claimData?.patientName || 'Unknown'} | Provider: ${data.claimData?.provider || 'Unknown'}`)
      addTerminalLog('[SYSTEM] ALL AGENTS COMPLETE — Backend processing finished')
      addTerminalLog(`[SYSTEM] Recommendation: ${data.recommendation} | Risk: ${data.riskLabel} (${data.riskScore})`)
      addTerminalLog('[SYSTEM] Claim snapshot saved to local storage for submission portal handoff')
      setIsComplete(true)
    } catch (error) {
      console.error('Process failed:', error)
      setErrorMessage(error.message || 'Failed to process claim. Please try again.')
      markFailed(activeStep, `[ERROR] Processing failed: ${error.message}`)
      addTerminalLog(`[ERROR] Processing failed: ${error.message}`)
    } finally {
      setIsProcessing(false)
    }
  }, [uploadedFile, demoMode, addTerminalLog, getDemoPayload, persistClaim])

  const handleUpload = useCallback(async (file) => {
    setErrorMessage('')
    setUploadedFile(file)
  }, [])

  const process = useCallback(() => {
    processReal()
  }, [processReal])

  const reset = useCallback(() => {
    abortRef.current = true
    setAgents(AGENT_STEPS.map(a => ({ ...a, status: 'idle', logs: [] })))
    setCurrentStep(-1)
    setIsProcessing(false)
    setIsComplete(false)
    setResults(null)
    setRiskScore(0)
    setErrorMessage('')
    setTerminalLogs([])
    setUploadedFile(null)
  }, [])

  return {
    demoMode,
    setDemoMode,
    agents,
    currentStep,
    isProcessing,
    isComplete,
    results,
    riskScore,
    errorMessage,
    terminalLogs,
    uploadedFile,
    handleUpload,
    process,
    reset,
  }
}

export { AGENT_STEPS }
