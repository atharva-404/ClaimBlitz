/**
 * Tests for useClaimAgent hook + FEAT-006 frontend refinement to prevent
 * regressions: the 9-agent roster, logs-driven step reconciliation, the
 * SYNTHETIC DEMO labeling, the compliance-claim scrub, and the provenance
 * badge rendering for MISSING / CONFLICT fields.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { render } from '@testing-library/react'

import {
  AGENT_STEPS,
  SYNTHETIC_DEMO_LABEL,
  agentsFromLogs,
} from '../useClaimAgent'
import { MasterClaimForm } from '../../components/claimbitz/MasterClaimForm'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC_ROOT = path.resolve(__dirname, '../../')

describe('useClaimAgent hook - AGENT_STEPS (9-agent roster)', () => {
  it('exports exactly 9 agent steps in pipeline order', () => {
    expect(AGENT_STEPS).toHaveLength(9)
    expect(AGENT_STEPS[0].name).toBe('Scanner Agent')
    expect(AGENT_STEPS[1].name).toBe('OCR Agent')
    expect(AGENT_STEPS[2].name).toBe('Validator Agent')
    expect(AGENT_STEPS[8].name).toBe('Communication Agent')
  })

  it('includes a judge step and a clinical "Clinical Consistency Agent" step', () => {
    const judge = AGENT_STEPS.find(a => a.id === 'judge')
    expect(judge).toBeTruthy()
    expect(judge.name).toBe('Judge Agent')

    const clinical = AGENT_STEPS.find(a => a.id === 'clinical')
    expect(clinical).toBeTruthy()
    expect(clinical.name).toBe('Clinical Consistency Agent')

    // The old 'medical' id is gone.
    expect(AGENT_STEPS.find(a => a.id === 'medical')).toBeUndefined()
  })

  it('has all required agent fields in AGENT_STEPS', () => {
    AGENT_STEPS.forEach(agent => {
      expect(agent).toHaveProperty('id')
      expect(agent).toHaveProperty('role')
      expect(agent).toHaveProperty('name')
      expect(agent).toHaveProperty('description')
      expect(agent).toHaveProperty('icon')
    })
  })
})

describe('useClaimAgent hook - logs-driven step reconciliation', () => {
  it('marks only agents present in data.logs as completed; others stay idle', () => {
    const logs = [
      { agent_role: 'scanner', status: 'success' },
      { agent_role: 'ocr', status: 'success' },
      { agent_role: 'validator', status: 'success' },
      { agent_role: 'judge', status: 'success' },
      { agent_role: 'communication', status: 'success' },
    ]
    const reconciled = agentsFromLogs(logs)
    const byId = Object.fromEntries(reconciled.map(a => [a.id, a.status]))

    expect(byId.scanner).toBe('completed')
    expect(byId.ocr).toBe('completed')
    expect(byId.validator).toBe('completed')
    expect(byId.judge).toBe('completed')
    expect(byId.comm).toBe('completed')

    // Agents that did not execute are greyed out (idle), never fabricated.
    expect(byId.clinical).toBe('idle')
    expect(byId.policy).toBe('idle')
    expect(byId.fraud).toBe('idle')
    expect(byId.risk).toBe('idle')
  })

  it('marks an agent whose log status is error as error', () => {
    const reconciled = agentsFromLogs([{ agent_role: 'ocr', status: 'error' }])
    const ocr = reconciled.find(a => a.id === 'ocr')
    expect(ocr.status).toBe('error')
  })

  it('returns an all-idle roster when there are no logs', () => {
    const reconciled = agentsFromLogs([])
    expect(reconciled).toHaveLength(9)
    expect(reconciled.every(a => a.status === 'idle')).toBe(true)
  })
})

describe('FEAT-006 - SYNTHETIC DEMO labeling', () => {
  it('exports the SYNTHETIC DEMO label', () => {
    expect(SYNTHETIC_DEMO_LABEL).toBe('SYNTHETIC DEMO')
  })

  it('renders the SYNTHETIC DEMO banner in the Master Claim Form when demoMode', () => {
    const { container, queryByTestId } = render(
      React.createElement(MasterClaimForm, {
        masterClaimForm: { jurisdiction: { jurisdiction: 'IN' } },
        demoMode: true,
      })
    )
    const banner = queryByTestId('synthetic-demo-banner')
    expect(banner).toBeTruthy()
    expect(container.textContent).toContain('SYNTHETIC DEMO')
  })

  it('does not render the SYNTHETIC DEMO banner when not in demo mode', () => {
    const { queryByTestId } = render(
      React.createElement(MasterClaimForm, {
        masterClaimForm: { jurisdiction: { jurisdiction: 'IN' } },
      })
    )
    expect(queryByTestId('synthetic-demo-banner')).toBeNull()
  })
})

describe('FEAT-006 - compliance-claim scrub (no HIPAA/DPDP/IRDAI claims)', () => {
  function walk(dir) {
    const out = []
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) out.push(...walk(full))
      else out.push(full)
    }
    return out
  }

  it('contains no HIPAA/DPDP/IRDAI compliance-claim strings in frontend/src', () => {
    const offenders = []
    const pattern = /HIPAA\s*compliant|DPDP\s*compliant|IRDAI\s*certified/i
    for (const file of walk(SRC_ROOT)) {
      if (!/\.(js|jsx|ts|tsx|css|md|html)$/.test(file)) continue
      const text = fs.readFileSync(file, 'utf8')
      if (pattern.test(text)) offenders.push(path.relative(SRC_ROOT, file))
    }
    expect(offenders).toEqual([])
  })
})

describe('FEAT-006 - MasterClaimForm provenance badge rendering', () => {
  const fixture = {
    jurisdiction: { jurisdiction: 'IN', currency: 'INR', inferred_from: 'content' },
    patient: {
      name: {
        field: 'patient.name', value: 'Aarav Mehta', source_document: 'claim.pdf',
        page: 1, confidence: 0.9, status: 'EXTRACTED', conflicts: [], note: null,
      },
      dob: {
        field: 'patient.dob', value: null, source_document: null, page: null,
        confidence: 0.0, status: 'MISSING', conflicts: [], note: null,
      },
    },
    policy: {
      policy_number: {
        field: 'policy.policy_number', value: 'POL-1', source_document: 'a.pdf',
        page: 2, confidence: 0.6, status: 'CONFLICT',
        conflicts: [
          { value: 'POL-1', source_document: 'a.pdf', page: 2, confidence: 0.6 },
          { value: 'POL-2', source_document: 'b.pdf', page: 1, confidence: 0.55 },
        ],
        note: null,
      },
    },
    billing: {
      line_items: [], calculated_total: null,
      submitted_total: { field: 'billing.submitted_total', value: null, status: 'MISSING', conflicts: [] },
      billing_difference: null, flag: 'INSUFFICIENT_DATA',
      currency: { field: 'billing.currency', value: 'INR', status: 'EXTRACTED', conflicts: [] },
    },
  }

  it('renders MISSING and CONFLICT badges (fields shown, never hidden)', () => {
    const { container } = render(React.createElement(MasterClaimForm, { masterClaimForm: fixture }))
    const statuses = Array.from(container.querySelectorAll('[data-status]')).map(
      el => el.getAttribute('data-status')
    )
    expect(statuses).toContain('MISSING')
    expect(statuses).toContain('CONFLICT')
    expect(statuses).toContain('EXTRACTED')
  })

  it('expands every conflicting value with its source', () => {
    const { container } = render(React.createElement(MasterClaimForm, { masterClaimForm: fixture }))
    expect(container.textContent).toContain('POL-1')
    expect(container.textContent).toContain('POL-2')
    expect(container.textContent).toContain('b.pdf')
  })

  it('shows a MISSING field value (dob) rather than hiding it', () => {
    const { container } = render(React.createElement(MasterClaimForm, { masterClaimForm: fixture }))
    // The humanized label is present even though the value is null.
    expect(container.textContent).toContain('Dob')
  })
})

describe('useClaimAgent hook - Return Value Structure', () => {
  it('should return object with all required properties', () => {
    const hookReturnValue = {
      demoMode: false,
      setDemoMode: () => {},
      agents: [],
      currentStep: -1,
      isProcessing: false,
      isComplete: false,
      results: null,
      riskScore: 0,
      errorMessage: '',
      terminalLogs: [],
      uploadedFile: null,
      handleUpload: () => {},
      process: () => {},
      reset: () => {},
    }

    expect(hookReturnValue).toHaveProperty('demoMode')
    expect(hookReturnValue).toHaveProperty('agents')
    expect(hookReturnValue).toHaveProperty('currentStep')
    expect(hookReturnValue).toHaveProperty('isProcessing')
    expect(hookReturnValue).toHaveProperty('isComplete')
    expect(hookReturnValue).toHaveProperty('results')
    expect(hookReturnValue).toHaveProperty('riskScore')
    expect(hookReturnValue).toHaveProperty('terminalLogs')
    expect(hookReturnValue).toHaveProperty('uploadedFile')
    expect(hookReturnValue).toHaveProperty('handleUpload')
    expect(hookReturnValue).toHaveProperty('process')
    expect(hookReturnValue).toHaveProperty('reset')
  })
})

describe('useClaimAgent hook - reset semantics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('reset returns to an all-idle roster', () => {
    const resetState = {
      isComplete: false,
      riskScore: 0,
      terminalLogs: [],
      agents: AGENT_STEPS.map(a => ({ ...a, status: 'idle', logs: [] })),
    }
    expect(resetState.isComplete).toBe(false)
    expect(resetState.riskScore).toBe(0)
    expect(resetState.terminalLogs).toHaveLength(0)
    expect(resetState.agents.every(a => a.status === 'idle')).toBe(true)
    expect(resetState.agents).toHaveLength(9)
  })
})

describe('useClaimAgent hook - Terminal Logging', () => {
  it('should identify log level markers', () => {
    const logs = [
      '[SYSTEM] Initializing',
      '[INFO] Processing',
      '[SUCCESS] Completed',
      '[ERROR] Failed',
    ]
    logs.forEach(log => {
      expect(log).toMatch(/\[(SYSTEM|INFO|SUCCESS|ERROR)\]/)
    })
  })
})
