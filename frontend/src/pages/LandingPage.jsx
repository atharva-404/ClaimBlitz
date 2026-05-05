import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Zap, Shield, Brain, ArrowRight,
  Clock, AlertTriangle, DollarSign, CheckCircle2,
  ScanLine, ShieldCheck, Activity,
  Sparkles, Bot, ChevronDown, Cpu
} from 'lucide-react'

const fadeUp = {
  hidden: { opacity: 0, y: 50 },
  visible: (i = 0) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.12, duration: 0.7, ease: [0.16, 1, 0.3, 1] }
  })
}

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } }
}

/* ─── Hero ─── */
function Hero() {
  const navigate = useNavigate()
  return (
    <section className="relative min-h-[100svh] pt-28 pb-16 flex items-center justify-center overflow-hidden">
      {/* Animated orbs */}
      <div className="orb absolute w-[500px] h-[500px] bg-violet/20 top-[-10%] left-[15%]" style={{ animationDelay: '0s' }} />
      <div className="orb absolute w-[400px] h-[400px] bg-pink/15 bottom-[5%] right-[10%]" style={{ animationDelay: '3s' }} />
      <div className="orb absolute w-[300px] h-[300px] bg-cyan/10 top-[40%] right-[30%]" style={{ animationDelay: '5s' }} />

      {/* Grid */}
      <div className="absolute inset-0 grid-pattern" />

      {/* Radial spotlight */}
      <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse 70% 50% at 50% 40%, rgba(139,92,246,0.09) 0%, transparent 100%)' }} />

      <div className="relative z-10 max-w-5xl mx-auto px-5 sm:px-6 text-center">
        {/* Badge */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={0}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-violet/20 bg-violet-dim mb-10">
          <Sparkles className="w-4 h-4 text-violet" />
          <span className="text-sm text-violet font-semibold tracking-wide">Autonomous AI Agent System</span>
        </motion.div>

        {/* Title */}
        <motion.h1 variants={fadeUp} initial="hidden" animate="visible" custom={1}
          className="text-[clamp(2.6rem,9vw,5.5rem)] font-black tracking-tight leading-[1.03] mb-7">
          <span className="text-text">Binary Blitz</span><br />
          <span className="text-gradient">Claims at the Speed</span><br />
          <span className="text-gradient">of Thought</span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p variants={fadeUp} initial="hidden" animate="visible" custom={2}
          className="text-base md:text-lg text-text-muted max-w-2xl mx-auto mb-12 leading-relaxed">
          Four autonomous AI agents process, validate, analyze, and communicate medical claims
          in seconds — not days. Welcome to the future of healthcare insurance.
        </motion.p>

        {/* CTA */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={3}
          className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16 w-full">
          <motion.button onClick={() => navigate('/dashboard')}
            whileHover={{ scale: 1.06, boxShadow: '0 0 40px rgba(139,92,246,0.4)' }}
            whileTap={{ scale: 0.97 }}
            className="group relative w-full sm:w-auto px-9 py-4 rounded-2xl font-bold text-lg text-white overflow-hidden cursor-pointer">
            <div className="absolute inset-0 btn-shimmer" />
            <span className="relative flex items-center gap-3">
              <Bot className="w-5 h-5" />
              Launch Agent System
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
            </span>
          </motion.button>

          <motion.button
            onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
            className="w-full sm:w-auto px-8 py-4 rounded-2xl font-semibold text-text border border-border hover:border-violet/40 hover:bg-violet-dim transition-all cursor-pointer">
            See How It Works <ChevronDown className="w-4 h-4 inline ml-1" />
          </motion.button>
        </motion.div>

        {/* Stats */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={4}
          className="grid grid-cols-3 gap-6 max-w-md mx-auto">
          {[
            { val: '< 30s', lbl: 'Processing' },
            { val: '98.7%', lbl: 'Accuracy' },
            { val: '4', lbl: 'AI Agents' },
          ].map((s, i) => (
            <div key={i} className="text-center">
              <div className="text-2xl md:text-3xl font-extrabold text-violet">{s.val}</div>
              <div className="text-xs text-text-dim mt-1 uppercase tracking-wider">{s.lbl}</div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Scroll hint */}
      <motion.div className="absolute bottom-8 left-1/2 -translate-x-1/2"
        animate={{ y: [0, 12, 0] }} transition={{ duration: 2.5, repeat: Infinity }}>
        <ChevronDown className="w-6 h-6 text-violet/30" />
      </motion.div>
    </section>
  )
}

/* ─── Problem vs Solution ─── */
function ProblemSolution() {
  const problems = [
    { icon: Clock, text: 'Claims take 30–90 days to process' },
    { icon: AlertTriangle, text: 'Manual review causes 20% error rate' },
    { icon: DollarSign, text: '$262B lost annually to improper payments' },
  ]
  const solutions = [
    { icon: Zap, text: 'AI processes claims in under 30 seconds' },
    { icon: Shield, text: '98.7% accuracy with automated validation' },
    { icon: Brain, text: 'Real-time fraud detection & risk scoring' },
  ]

  return (
    <section className="py-28 px-6 relative">
      <div className="max-w-6xl mx-auto">
        <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }} className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            <span className="text-text">The Problem We </span><span className="text-danger">Crush</span>
          </h2>
          <p className="text-text-muted max-w-xl mx-auto">Traditional claims processing is broken. We rebuilt it from the ground up.</p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-10 relative">
          {/* Center divider */}
          <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-violet/25 to-transparent -translate-x-1/2" />

          {/* Problems */}
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true }} className="space-y-4">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-3 h-3 rounded-full bg-danger" />
              <h3 className="text-lg font-bold text-danger">Today's Reality</h3>
            </div>
            {problems.map((p, i) => (
              <motion.div key={i} variants={fadeUp} className="glass p-5 flex items-center gap-4 group" style={{ borderColor: 'rgba(251,113,133,0.1)' }}>
                <div className="w-11 h-11 rounded-xl bg-danger/10 flex items-center justify-center shrink-0">
                  <p.icon className="w-5 h-5 text-danger" />
                </div>
                <p className="text-text-muted group-hover:text-text transition-colors text-sm">{p.text}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Solutions */}
          <motion.div variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true }} className="space-y-4">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-3 h-3 rounded-full bg-violet" />
              <h3 className="text-lg font-bold text-violet">Binary Blitz Solution</h3>
            </div>
            {solutions.map((s, i) => (
              <motion.div key={i} variants={fadeUp} className="glass neon-active p-5 flex items-center gap-4 group">
                <div className="w-11 h-11 rounded-xl bg-violet-dim flex items-center justify-center shrink-0">
                  <s.icon className="w-5 h-5 text-violet" />
                </div>
                <p className="text-text font-medium text-sm">{s.text}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}

/* ─── Features / How It Works ─── */
function Features() {
  const features = [
    {
      icon: ScanLine, step: '01', title: 'Agentic Extraction',
      desc: 'Our Scanner Agent uses advanced OCR and NLP to extract every data point from claim forms with 98.7% accuracy.',
      details: ['CMS-1500 & UB-04 Forms', 'ICD-10 & CPT Parsing', 'Multi-format Support'],
    },
    {
      icon: ShieldCheck, step: '02', title: 'Automated Validation',
      desc: 'The Validator Agent cross-references data against policy rules, network status, and pre-auth requirements in real-time.',
      details: ['Policy Rule Engine', 'Network Verification', 'Duplicate Detection'],
    },
    {
      icon: Activity, step: '03', title: 'Instant Communication',
      desc: 'Risk Analyst scores each claim for fraud and errors. Comm Agent drafts personalized notifications across channels.',
      details: ['Real-time Risk Scoring', 'Auto-generated EOBs', 'Multi-channel Notifications'],
    },
  ]

  return (
    <section id="how-it-works" className="py-28 px-6 relative">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-violet/20 to-transparent" />
      <div className="max-w-6xl mx-auto">
        <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-80px' }} className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            <span className="text-text">How </span><span className="text-gradient">Binary Blitz</span><span className="text-text"> Works</span>
          </h2>
          <p className="text-text-muted max-w-lg mx-auto">Three steps. Four agents. One seamless pipeline.</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-7">
          {features.map((f, i) => (
            <motion.div key={i} custom={i} variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}
              whileHover={{ y: -10, transition: { duration: 0.3 } }}
              className="glass p-8 group relative overflow-hidden">
              {/* Big step bg */}
              <div className="absolute -top-4 right-2 text-[118px] font-black text-violet/[0.04] leading-none select-none pointer-events-none">{f.step}</div>

              <div className="w-14 h-14 rounded-2xl bg-violet-dim flex items-center justify-center mb-6 group-hover:bg-violet/20 transition-colors relative">
                <f.icon className="w-7 h-7 text-violet" />
              </div>

              <div className="text-[10px] font-mono text-text-dim mb-2 tracking-[0.2em] uppercase">Step {f.step}</div>
              <h3 className="text-xl font-bold text-text mb-3">{f.title}</h3>
              <p className="text-text-muted text-sm leading-relaxed mb-5">{f.desc}</p>

              <ul className="space-y-2.5">
                {f.details.map((d, j) => (
                  <li key={j} className="flex items-center gap-2.5 text-sm">
                    <CheckCircle2 className="w-4 h-4 text-violet/50 shrink-0" />
                    <span className="text-text-muted">{d}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
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
    <section className="py-28 px-6 relative">
      <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse 60% 50% at 50% 50%, rgba(139,92,246,0.06) 0%, transparent 100%)' }} />
      <motion.div variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}
        className="max-w-3xl mx-auto text-center relative z-10">
        <div className="glass p-14 md:p-20 neon-active noise relative overflow-hidden">
          <Cpu className="w-12 h-12 text-violet mx-auto mb-7" />
          <h2 className="text-3xl md:text-4xl font-bold text-text mb-5">Ready to Transform Claims Processing?</h2>
          <p className="text-text-muted mb-10 max-w-lg mx-auto">Experience four autonomous AI agents working in perfect harmony to process medical claims instantly.</p>
          <motion.button onClick={() => navigate('/dashboard')}
            whileHover={{ scale: 1.06, boxShadow: '0 0 50px rgba(139,92,246,0.4)' }}
            whileTap={{ scale: 0.95 }}
            className="group relative px-10 py-5 rounded-2xl font-bold text-lg text-white overflow-hidden glow-pulse cursor-pointer">
            <div className="absolute inset-0 btn-shimmer" />
            <span className="relative flex items-center gap-3">
              <Bot className="w-6 h-6" />
              Launch Agent System
              <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform" />
            </span>
          </motion.button>
        </div>
      </motion.div>
    </section>
  )
}

/* ─── Navbar ─── */
function Navbar() {
  const navigate = useNavigate()
  return (
    <motion.nav initial={{ y: -30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.6 }}
      className="fixed top-2 sm:top-0 left-0 right-0 z-50 px-3 sm:px-4 py-3">
      <div className="max-w-6xl mx-auto glass px-4 sm:px-5 py-3 flex items-center justify-between gap-3" style={{ borderRadius: '14px' }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-violet-dim flex items-center justify-center">
            <Zap className="w-5 h-5 text-violet" />
          </div>
          <span className="font-bold text-base sm:text-lg text-text tracking-tight">Binary Blitz</span>
        </div>
        <motion.button onClick={() => navigate('/dashboard')}
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          className="px-4 sm:px-5 py-2 rounded-xl bg-violet-dim border border-violet/25 text-violet text-sm font-semibold hover:bg-violet/20 transition-colors cursor-pointer">
          Open Dashboard
        </motion.button>
      </div>
    </motion.nav>
  )
}

/* ─── Page ─── */
export default function LandingPage() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}
      className="min-h-screen bg-base overflow-x-clip">
      <Navbar />
      <Hero />
      <ProblemSolution />
      <Features />
      <CTA />
      <footer className="py-8 px-6 border-t border-border">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2 text-text-dim text-sm">
            <Zap className="w-4 h-4 text-violet" />
            <span>Binary Blitz © 2026 — Built for DYP Hackathon</span>
          </div>
          <div className="text-sm text-text-dim/50">Autonomous Medical Claim Agent System</div>
        </div>
      </footer>
    </motion.div>
  )
}
