import React from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ShieldCheck, ArrowRight, ScanLine, Activity, MessageSquare,
  Clock, AlertTriangle, DollarSign, CheckCircle2, FileSearch, Gauge,
} from 'lucide-react'
import { Button, Card, Badge } from '../components/ui'

/* ─── Navbar ─── */
function Navbar() {
  const navigate = useNavigate()
  return (
    <header className="sticky top-0 z-50 border-b border-default bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3 lg:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <span className="text-base font-semibold text-primary">ClaimBitz</span>
        </div>
        <Button variant="primary" size="sm" onClick={() => navigate('/dashboard')}>
          Open console
        </Button>
      </div>
    </header>
  )
}

/* ─── Hero ─── */
function Hero() {
  const navigate = useNavigate()
  return (
    <section className="border-b border-default bg-surface">
      <div className="mx-auto max-w-4xl px-5 py-20 text-center lg:px-8 lg:py-28">
        <div className="mb-6 inline-flex">
          <Badge variant="brand">
            <ShieldCheck className="h-3.5 w-3.5" />
            Multi-agent claim analysis
          </Badge>
        </div>
        <h1 className="text-4xl font-bold leading-tight tracking-tight text-primary sm:text-5xl">
          Medical claim processing,<br className="hidden sm:block" /> reviewed in seconds
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-secondary">
          ClaimBitz reads a claim document, validates it, checks clinical and policy rules,
          detects fraud signals, scores rejection risk, and drafts the response — with a full,
          auditable trail of how each decision was made.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button variant="primary" size="lg" onClick={() => navigate('/dashboard')}>
            Launch console
            <ArrowRight className="h-5 w-5" />
          </Button>
          <Button
            variant="secondary"
            size="lg"
            onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
          >
            How it works
          </Button>
        </div>

        {/* Stats */}
        <div className="mx-auto mt-14 grid max-w-2xl grid-cols-3 gap-6 border-t border-default pt-8">
          {[
            { val: 'Under 30s', lbl: 'Median processing time' },
            { val: '98.7%', lbl: 'Validation accuracy' },
            { val: '9 agents', lbl: 'Collaborative pipeline' },
          ].map((s) => (
            <div key={s.lbl}>
              <div className="text-xl font-bold text-primary sm:text-2xl">{s.val}</div>
              <div className="mt-1 text-xs text-secondary sm:text-sm">{s.lbl}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Capabilities ─── */
function Capabilities() {
  const items = [
    { icon: FileSearch, title: 'Automated intake', desc: 'Scanner and OCR agents extract every field from PDFs and images, then validate format and consistency.' },
    { icon: Activity, title: 'AI-assisted analysis', desc: 'Medical, policy, and fraud specialists review each claim in parallel against clinical and coverage rules.' },
    { icon: Gauge, title: 'Risk detection', desc: 'A calibrated risk score and category surface rejection likelihood before the claim is submitted.' },
    { icon: MessageSquare, title: 'Actionable outputs', desc: 'Ready-to-send email and messaging drafts, a claim summary, and per-agent findings — all in one place.' },
  ]
  return (
    <section className="bg-canvas">
      <div className="mx-auto max-w-6xl px-5 py-20 lg:px-8">
        <div className="mb-12 max-w-2xl">
          <h2 className="text-2xl font-bold tracking-tight text-primary sm:text-3xl">
            Built for claims operations
          </h2>
          <p className="mt-3 text-secondary">
            Every step is explainable and auditable, so reviewers stay in control of the decision.
          </p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((it) => (
            <Card key={it.title} className="p-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-brand-subtle">
                <it.icon className="h-5 w-5 text-brand" />
              </div>
              <h3 className="mt-4 text-base font-semibold text-primary">{it.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-secondary">{it.desc}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Problem / solution ─── */
function ProblemSolution() {
  const problems = [
    { icon: Clock, text: 'Claims take 30–90 days to process' },
    { icon: AlertTriangle, text: 'Manual review drives a high error rate' },
    { icon: DollarSign, text: 'Billions lost annually to improper payments' },
  ]
  const solutions = [
    { text: 'Documents processed in under 30 seconds' },
    { text: '98.7% accuracy with automated validation' },
    { text: 'Real-time fraud detection and risk scoring' },
  ]
  return (
    <section className="border-y border-default bg-surface">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-20 md:grid-cols-2 lg:px-8">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Today's reality</h3>
          <ul className="mt-5 space-y-3">
            {problems.map((p, i) => (
              <li key={i} className="flex items-center gap-3 rounded-lg border border-default bg-canvas p-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-error-subtle">
                  <p.icon className="h-4 w-4 text-error" />
                </span>
                <span className="text-sm text-secondary">{p.text}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-brand">With ClaimBitz</h3>
          <ul className="mt-5 space-y-3">
            {solutions.map((s, i) => (
              <li key={i} className="flex items-center gap-3 rounded-lg border border-default bg-canvas p-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-success-subtle">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                </span>
                <span className="text-sm font-medium text-primary">{s.text}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

/* ─── How it works ─── */
function HowItWorks() {
  const steps = [
    { icon: ScanLine, step: '01', title: 'Intake & extraction', desc: 'Scanner, OCR, and Validator agents ingest the document and structure every field.' },
    { icon: Activity, step: '02', title: 'Parallel analysis', desc: 'Medical, Policy, Fraud, and Risk agents review the claim concurrently, each with its own memory.' },
    { icon: ShieldCheck, step: '03', title: 'Decision & output', desc: 'On disagreement, a debate round and Judge ruling resolve the outcome, then communications are drafted.' },
  ]
  return (
    <section id="how-it-works" className="bg-canvas">
      <div className="mx-auto max-w-6xl px-5 py-20 lg:px-8">
        <div className="mb-12 max-w-2xl">
          <h2 className="text-2xl font-bold tracking-tight text-primary sm:text-3xl">How it works</h2>
          <p className="mt-3 text-secondary">Three phases. Nine agents. One auditable pipeline.</p>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {steps.map((f) => (
            <Card key={f.step} className="p-6">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-brand-subtle">
                  <f.icon className="h-5 w-5 text-brand" />
                </span>
                <span className="font-mono text-sm font-semibold text-muted">{f.step}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-primary">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-secondary">{f.desc}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── CTA ─── */
function CTA() {
  const navigate = useNavigate()
  return (
    <section className="border-t border-default bg-surface">
      <div className="mx-auto max-w-3xl px-5 py-20 text-center lg:px-8">
        <h2 className="text-2xl font-bold tracking-tight text-primary sm:text-3xl">
          Ready to review claims faster?
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-secondary">
          Open the console and run a claim through the full multi-agent pipeline.
        </p>
        <Button variant="primary" size="lg" className="mt-8" onClick={() => navigate('/dashboard')}>
          Launch console
          <ArrowRight className="h-5 w-5" />
        </Button>
      </div>
    </section>
  )
}

/* ─── Page ─── */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-canvas">
      <Navbar />
      <Hero />
      <Capabilities />
      <ProblemSolution />
      <HowItWorks />
      <CTA />
      <footer className="border-t border-default bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 py-8 text-sm text-muted md:flex-row lg:px-8">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-brand" />
            <span>ClaimBitz © 2026</span>
          </div>
          <span>Multi-agent medical claim processing</span>
        </div>
      </footer>
    </div>
  )
}
