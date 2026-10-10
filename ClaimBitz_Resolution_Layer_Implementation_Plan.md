# ClaimBitz Resolution Layer — Implementation Plan

## Objective

Evolve ClaimBitz from primarily an AI-powered **claim review and risk assessment system** into an **actionable claims operations workflow**.

The product should not stop at:

> Claim → Review → Risk → Recommendation

It should communicate and support:

> Claim → Understand → Validate → Detect → Decide → Resolve → Verify → Audit

The goal is not to build an autonomous insurance adjudication system. ClaimBitz remains human-in-the-loop and recommends, prepares, routes, and tracks appropriate actions based on claim findings.

---

## Current State

ClaimBitz already provides:

- CMS-1500-style claim upload
- OCR / extraction
- Claim validation
- Medical analysis
- Policy analysis
- Fraud/anomaly analysis
- Risk assessment
- Risk reasons/findings
- Email / WhatsApp generated communication
- Insurer portal workflow
- Processing logs
- Audit-oriented history
- Demo Mode with LOW / MEDIUM / HIGH scenarios
- Full 8-agent sequential demo execution

### Current gap

The completed result communicates **what was found** well, but the **resolution path / next operational action** is not yet equally explicit.

---

# Product Resolution Model

## 1. Understand

Read and extract the claim.

## 2. Validate

Check structure, required information, medical consistency, policy information, and billing/coding details.

## 3. Detect

Identify risk indicators, anomalies, and potential fraud signals.

## 4. Decide

Produce:

- Risk level
- Reasons
- Findings
- Recommendation

## 5. Resolve

Turn the recommendation into an operational next step.

Possible paths:

### Low Risk

- Proceed toward approval / submission
- Continue to insurer portal where applicable

### Medium Risk

- Request clarification or missing information
- Generate communication
- Route for human review
- Re-process after additional information is received

### High Risk

- Escalate for investigation
- Route to human reviewer/investigator
- Preserve findings and evidence
- Continue tracking the case

## 6. Verify

Where the existing workflow supports it:

- Confirm an action was prepared/submitted
- Confirm the claim moved to the intended state
- Allow re-processing after new information
- Never claim successful external submission unless it is actually verified

## 7. Audit

Preserve:

- Agent findings
- Risk assessment
- Recommendation
- Action taken
- Communication generated
- Review/escalation state
- Processing timeline

---

# Core Product Principle

ClaimBitz should communicate:

> **“We don't just tell you what is wrong with a claim. We turn the findings into the next actionable workflow.”**

The system must remain honest about what it actually executes.

Do not claim automatic approval, denial, fraud determination, insurer submission, or external resolution unless the existing backend/integration genuinely performs and verifies that action.

---

# UI Plan

## Phase 1 — Result / Resolution Layer

Add a clear section after the risk assessment.

Show:

- Risk score
- Risk label
- Short status
- Key findings

Then introduce:

### Recommended Action

This should be visually distinct from the risk score.

Examples:

**LOW**
> Proceed with approval

**MEDIUM**
> Request clarification / human review

**HIGH**
> Escalate for investigation

The action should come from the existing real recommendation where available. Do not invent production actions that the backend does not support.

---

# Phase 2 — Action Controls

Connect the recommended action to existing real functionality.

Potential existing actions include:

- Continue to insurer portal
- Generate communication
- Email
- WhatsApp
- Review
- Reset / re-process

Do not add fake buttons.

Every new button must either:

1. execute an existing real workflow,
2. navigate to an existing real workflow,
3. prepare an action using existing functionality, or
4. be clearly marked as a non-executing recommendation if no execution exists.

---

# Phase 3 — Finding → Action Relationship

Make it visually obvious why the recommended action exists.

Example:

```text
Finding
Diagnosis/procedure inconsistency
        ↓
Risk
MEDIUM
        ↓
Recommended Action
Request clarification
        ↓
Available Action
Generate clarification request
```

For HIGH:

```text
Finding
Billing frequency anomaly
        ↓
Risk
HIGH
        ↓
Recommended Action
Escalate for investigation
        ↓
Available Action
Open human review / investigation workflow
```

Only implement actions supported by the existing application.

---

# Phase 4 — Portal Continuation

Use the existing insurer portal flow as part of the resolution story.

```text
Claim analyzed
↓
Risk assessed
↓
Recommendation
↓
Continue to insurer portal
↓
Submission/application workflow
↓
Audit
```

Do not redesign the portal unnecessarily.

Make the portal feel like a continuation of the claim workflow rather than an unrelated route.

---

# Phase 5 — Medium-Risk Exception Workflow

Make MEDIUM the clearest demonstration of human-in-the-loop resolution.

Target flow:

```text
Claim
↓
Analysis
↓
Issue detected
↓
MEDIUM risk
↓
Clarification / review recommended
↓
Generate communication
↓
Human review
↓
Re-process when information is available
```

Use existing communication functionality where possible.

Do not invent an external provider-response system unless the application already supports it.

---

# Phase 6 — High-Risk Escalation

HIGH should communicate:

```text
Suspicious / inconsistent indicators
↓
HIGH risk
↓
Human investigation required
↓
Findings preserved
↓
Reviewer takes action
↓
Audit trail
```

Do not label a claim as definitively fraudulent solely because the fraud agent found indicators.

Use wording such as:

- suspicious indicator
- potential anomaly
- investigation recommended
- human review required

---

# Phase 7 — Verification / State Integrity

Audit all action states.

Required behavior:

- Loading state
- Action available
- Action in progress
- Action completed
- Action failed
- Retry where appropriate
- No false success states
- No fake external submission confirmation

If the system only prepares a communication rather than sending it, distinguish:

> Generated

from:

> Sent

If the portal is only opened rather than submission being verified, distinguish:

> Ready to submit

from:

> Submitted

---

# Phase 8 — Motion / UX Refinement

Use motion to explain causality rather than decorate the interface.

Desired result flow:

```text
Risk revealed
↓
Findings revealed
↓
Recommended action revealed
↓
Action controls revealed
```

Guidelines:

- Risk score: primary reveal
- Findings: secondary staggered reveal
- Recommended action: strong but restrained reveal
- Action controls: subtle entrance
- Completed agents: quiet state
- Active agent: noticeable state
- Final resolution: strongest transition in the workflow
- Avoid excessive bouncing, glow, or continuous animation
- Respect reduced-motion settings

The final result should feel like the culmination of the 8-agent pipeline.

---

# Phase 9 — Landing Page Product Story

Keep the current visual identity but clarify the next step.

Concept:

> **Read. Validate. Decide. Resolve.**

Possible supporting message:

> Turn every claim review into an actionable, auditable resolution.

Landing-page story:

```text
CLAIM
↓
UNDERSTAND
↓
VALIDATE
↓
ANALYZE
↓
DECIDE
↓
RESOLVE
↓
AUDIT
```

Do not overload the landing page with implementation details. The landing page explains business value; the dashboard demonstrates the detailed 8-agent workflow.

---

# Phase 10 — Dashboard Product Story

The dashboard should clearly communicate:

```text
INPUT
↓
8-AGENT ANALYSIS
↓
RISK + FINDINGS
↓
RECOMMENDED ACTION
↓
OPERATIONAL NEXT STEP
↓
AUDIT
```

It should answer immediately:

1. What did ClaimBitz find?
2. Why did it reach this recommendation?
3. What should happen next?

---

# Demo Mode Requirements

LOW / MEDIUM / HIGH must continue using the complete 8-agent sequential pipeline:

```text
Scanner
↓
OCR
↓
Validator
↓
Medical
↓
Policy
↓
Fraud
↓
Risk
↓
Communications
↓
Final Result
```

Scenario differences should affect:

- findings
- risk
- recommendation
- resolution path

Demo Mode must remain isolated from real claim processing.

---

# Real Data Integrity

Production/real mode must continue to use:

- actual uploaded claim
- actual backend `/process` result
- actual claimData
- actual riskScore/riskLabel
- actual riskReasons
- actual recommendation
- actual findings
- actual communication output
- actual processing logs

Missing data must remain `—`.

Never create fake production values merely to fill UI space.

---

# Architecture Constraints

Preserve:

- React 18
- Vite
- React Router
- Existing `useClaimAgent`
- Existing 8-agent architecture
- Existing FastAPI `/process`
- Existing upload flow
- Existing demo mode
- Existing localStorage compatibility
- Existing insurer portal route
- Existing submission route
- Existing communication functionality

Do not migrate frameworks.

Do not add a state-management library solely for this feature.

Do not create a second processing engine.

Do not create a separate fake resolution engine disconnected from the real state.

---

# Verification Checklist

## Functional

- [ ] LOW result exposes a valid next action
- [ ] MEDIUM result exposes a valid review/clarification path
- [ ] HIGH result exposes a valid escalation path
- [ ] Existing portal flow still works
- [ ] Existing communication flow still works
- [ ] Real claim processing remains unchanged
- [ ] Demo processing remains sequential
- [ ] Reset remains functional
- [ ] Errors remain functional
- [ ] No fake success state
- [ ] No unsupported action claims

## UI

- [ ] Risk → Findings → Action hierarchy is clear
- [ ] Action section does not overpower risk
- [ ] Existing copper/warm-neutral palette preserved
- [ ] No blue/purple/neon/glassmorphism
- [ ] No unnecessary cards or visual clutter
- [ ] Desktop layout verified
- [ ] Narrow/mobile layout verified
- [ ] Buttons have clear enabled/disabled/loading states

## Motion

- [ ] Result reveal has intentional sequencing
- [ ] Findings reveal naturally
- [ ] Recommended action enters after findings
- [ ] Action controls enter after recommendation
- [ ] No excessive animation
- [ ] Reduced-motion behavior preserved

## Technical

- [ ] `npm run build`
- [ ] `npx vitest run`
- [ ] No new console errors
- [ ] No mock production data
- [ ] No unused resolution code
- [ ] No changes to main
- [ ] One focused commit per meaningful phase

---

# Git Workflow

Use:

```text
feature/claimbitz-final-lovable-parity
```

Workflow:

```text
Audit
↓
Implement one focused phase
↓
Build
↓
Test
↓
Review diff
↓
Commit
↓
Push
↓
Report
↓
Next phase
```

Do not merge or create a PR until the user reviews the complete result.

---

# Definition of Done

ClaimBitz is complete for this phase when a user can look at a processed claim and immediately understand:

> **What did the system find?**

> **Why did it reach that conclusion?**

> **What should happen next?**

> **How can I take that next action using ClaimBitz?**

> **Where is the record of what happened?**

Final product story:

> **ClaimBitz turns a medical claim from a static document into an intelligent, explainable, actionable, and auditable claims workflow.**
