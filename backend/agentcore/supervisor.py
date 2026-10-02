"""Supervisor orchestration engine.

The Supervisor is NOT "just another agent" — it is the workflow controller
that drives claims through the multi-agent pipeline. It owns the
``ClaimWorkflowState`` for each in-flight claim and decides what happens
next based on:
- The current ``ClaimStage``
- The results returned by agents it dispatches work to
- Disagreement detection (do analysts' verdicts conflict?) — recorded as
  evidence only; it never decides the outcome
- The Judge's ruling, which is the single decision authority

Workflow state machine:
  INGESTED -> SCANNING -> OCR_EXTRACTION -> VALIDATION
  -> PARALLEL_ANALYSIS (the four analysts, spaced by a rate-limit delay)
  -> DEBATE (only when analysts disagree — records DebateRounds as evidence)
  -> JUDGMENT (the Judge ALWAYS rules; blocking conditions force REVIEW)
  -> (if requires_human_review / blocking) HUMAN_ESCALATION
  -> COMMUNICATION -> COMPLETED | REJECTED

Resilience (design §14): one agent failing never crashes the pipeline. Each
stage wraps its agent call; on ``LLMAllProvidersFailedError``/``Exception`` it
synthesizes a role-keyed ABSTAIN finding (tagged ``agent_unavailable``),
records an ``error`` step log, and continues. For an OCR failure the Master
Claim Form stays the all-MISSING baseline so nothing is fabricated.

The Supervisor talks to agents by awaiting their ``analyze()`` directly
(in-process mode) rather than going through the message bus — this is
simpler, avoids circular bus subscriptions, and the bus exists for
*agent-to-agent* communication (peer questions, objections), not for the
orchestrator-to-agent dispatch pattern.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .agents.communication import CommunicationAgent
from .agents.fraud_detection import FraudDetectionAgent
from .agents.judge import JudgeAgent
from .agents.medical_expert import MedicalExpertAgent
from .agents.ocr import OCRAgent
from .agents.policy_expert import PolicyExpertAgent
from .agents.risk_assessment import RiskAssessmentAgent
from .agents.scanner import ScannerAgent
from .agents.validator import ValidatorAgent
from .llm import LLMAllProvidersFailedError
from .protocol import (
    AGENT_DISPLAY_NAMES,
    AgentFinding,
    AgentRole,
    ClaimStage,
    ClaimWorkflowState,
    ConfidenceScore,
    DebateRound,
    DecisionPath,
    DecisionStep,
    EscalationReason,
    HumanEscalation,
    JudgeRuling,
    PARALLEL_ANALYST_ROLES,
    Verdict,
    now_utc,
)

logger = logging.getLogger(__name__)

MAX_DEBATE_ROUNDS = 2


class Supervisor:
    """Workflow orchestrator for the multi-agent claim pipeline."""

    def __init__(
        self,
        *,
        scanner: ScannerAgent,
        ocr: OCRAgent,
        validator: ValidatorAgent,
        medical_expert: MedicalExpertAgent,
        policy_expert: PolicyExpertAgent,
        fraud_detection: FraudDetectionAgent,
        risk_assessment: RiskAssessmentAgent,
        communication: CommunicationAgent,
        judge: JudgeAgent,
    ) -> None:
        self.scanner = scanner
        self.ocr = ocr
        self.validator = validator
        self.medical_expert = medical_expert
        self.policy_expert = policy_expert
        self.fraud_detection = fraud_detection
        self.risk_assessment = risk_assessment
        self.communication = communication
        self.judge = judge

        self._analysts: dict[AgentRole, Any] = {
            AgentRole.MEDICAL_EXPERT: self.medical_expert,
            AgentRole.POLICY_EXPERT: self.policy_expert,
            AgentRole.FRAUD_DETECTION: self.fraud_detection,
            AgentRole.RISK_ASSESSMENT: self.risk_assessment,
        }

    async def process_claim(
        self,
        *,
        claim_id: str,
        raw_text: str,
        file_meta: dict[str, Any] | None = None,
    ) -> ClaimWorkflowState:
        """Drive a claim through the entire pipeline end-to-end.

        Returns the final ``ClaimWorkflowState`` snapshot.
        """
        dp = DecisionPath(claim_id=claim_id)
        state = ClaimWorkflowState(
            claim_id=claim_id,
            stage=ClaimStage.INGESTED,
            decision_path=dp,
        )
        # Private runtime carriers (plain attribute assignment per protocol
        # convention — these are not part of the serialized state model).
        state._extracted_claim = {}  # type: ignore[attr-defined]
        state._comm_drafts = {}  # type: ignore[attr-defined]
        state._step_logs = []  # type: ignore[attr-defined]
        state._agent_claim = {}  # type: ignore[attr-defined]
        state._jurisdiction = None  # type: ignore[attr-defined]
        self._trace_id = file_meta.get("trace_id") if file_meta else None  # type: ignore[attr-defined]

        try:
            file_meta = file_meta or {}
            state = await self._run_scanning(state, file_meta)
            if state.stage in (ClaimStage.REJECTED, ClaimStage.FAILED):
                return state

            await asyncio.sleep(1.5)  # Rate limit delay

            state = await self._run_ocr(state, raw_text, file_meta)
            if state.stage in (ClaimStage.REJECTED, ClaimStage.FAILED):
                return state

            await asyncio.sleep(1.5)  # Rate limit delay

            state = await self._run_validation(state)
            # Validation issues are noted but DON'T stop the pipeline.
            # Only Scanner rejection (unprocessable file) stops early.
            # The parallel analysts will factor in validation issues.
            if state.stage == ClaimStage.REJECTED:
                state.stage = ClaimStage.VALIDATION  # downgrade to continue

            state = await self._run_parallel_analysis(state)
            state = await self._resolve_disagreement(state)
            state = await self._run_judgment(state)
            state = await self._run_communication(state)

        except Exception as exc:
            logger.exception("Supervisor pipeline failed for %s", claim_id)
            state.stage = ClaimStage.FAILED
            state.decision_path = state.decision_path.append(
                DecisionStep(
                    agent=AgentRole.SUPERVISOR,
                    action="pipeline_failed",
                    summary=str(exc),
                )
            )

        state.updated_at = now_utc()
        return state

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    async def _run_scanning(
        self, state: ClaimWorkflowState, file_meta: dict[str, Any]
    ) -> ClaimWorkflowState:
        state.stage = ClaimStage.SCANNING
        started = time.perf_counter()
        try:
            finding = await self.scanner.analyze(
                claim_id=state.claim_id, claim={"file_meta": file_meta}
            )
        except (LLMAllProvidersFailedError, Exception) as exc:  # noqa: BLE001
            logger.error("Scanner failed: %s", exc)
            finding = self._abstain_finding(AgentRole.SCANNER, state.claim_id, exc)
            state.findings.append(finding)
            self._log_step(
                state, AgentRole.SCANNER, "scanned_document",
                started=started, status="error", finding=finding, error=str(exc),
                input_summary="file_meta",
            )
            return state

        state.findings.append(finding)
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.SCANNER,
                action="scanned_document",
                summary=finding.reasoning,
                confidence=finding.confidence,
            )
        )
        self._log_step(
            state, AgentRole.SCANNER, "scanned_document",
            started=started, status="ok", finding=finding,
            input_summary="file_meta", output_summary=finding.reasoning[:120],
        )
        if finding.verdict == Verdict.REJECT:
            state.stage = ClaimStage.REJECTED
        return state

    async def _run_ocr(
        self,
        state: ClaimWorkflowState,
        raw_text: str,
        file_meta: dict[str, Any] | None = None,
    ) -> ClaimWorkflowState:
        """Build the Master Claim Form ONCE (single widened extraction).

        No second ``extract()``/``analyze()`` call — the OCR finding is derived
        from the same extraction result (design §6.1 step 4 / §7).
        """
        state.stage = ClaimStage.OCR_EXTRACTION
        source_document = (file_meta or {}).get("filename")
        started = time.perf_counter()

        try:
            form, extracted = await self.ocr.build_master_form(
                claim_id=state.claim_id,
                raw_text=raw_text,
                source_document=source_document,
            )
        except (LLMAllProvidersFailedError, Exception) as exc:  # noqa: BLE001
            logger.error("OCR failed: %s", exc)
            # Leave master_form as the all-MISSING baseline so nothing is
            # fabricated; synthesize an ABSTAIN finding and continue.
            from .claim_model import build_empty_master_form, infer_jurisdiction

            profile = infer_jurisdiction(raw_text, None)
            form = build_empty_master_form(state.claim_id, profile)
            state.master_form = form.model_dump(mode="json")
            state._extracted_claim = {}  # type: ignore[attr-defined]
            state._jurisdiction = profile  # type: ignore[attr-defined]
            state._agent_claim = self._build_agent_claim(form, profile, {})  # type: ignore[attr-defined]
            finding = self._abstain_finding(AgentRole.OCR, state.claim_id, exc)
            state.findings.append(finding)
            self._log_step(
                state, AgentRole.OCR, "extracted_fields",
                started=started, status="error", finding=finding, error=str(exc),
                input_summary=f"raw_text[{len(raw_text)}]",
            )
            return state

        profile = form.jurisdiction
        state.master_form = form.model_dump(mode="json")
        state._extracted_claim = extracted  # type: ignore[attr-defined]
        state._jurisdiction = profile  # type: ignore[attr-defined]
        state._agent_claim = self._build_agent_claim(form, profile, extracted)  # type: ignore[attr-defined]

        finding = self.ocr.finding_from_extraction(
            claim_id=state.claim_id, extracted=extracted, raw_text=raw_text
        )
        state.findings.append(finding)
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.OCR,
                action="extracted_fields",
                summary=finding.reasoning,
                confidence=finding.confidence,
            )
        )
        self._log_step(
            state, AgentRole.OCR, "extracted_fields",
            started=started, status="ok", finding=finding,
            input_summary=f"raw_text[{len(raw_text)}]",
            output_summary=finding.reasoning[:120],
        )
        return state

    async def _run_validation(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        state.stage = ClaimStage.VALIDATION
        claim_data = self._agent_claim(state)
        started = time.perf_counter()
        try:
            finding = await self.validator.analyze(
                claim_id=state.claim_id, claim=claim_data
            )
        except (LLMAllProvidersFailedError, Exception) as exc:  # noqa: BLE001
            logger.error("Validator failed: %s", exc)
            finding = self._abstain_finding(AgentRole.VALIDATOR, state.claim_id, exc)
            state.findings.append(finding)
            self._log_step(
                state, AgentRole.VALIDATOR, "validated_fields",
                started=started, status="error", finding=finding, error=str(exc),
                input_summary="master_form",
            )
            return state

        state.findings.append(finding)
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.VALIDATOR,
                action="validated_fields",
                summary=finding.reasoning,
                confidence=finding.confidence,
            )
        )
        self._log_step(
            state, AgentRole.VALIDATOR, "validated_fields",
            started=started, status="ok", finding=finding,
            input_summary="master_form", output_summary=finding.reasoning[:120],
        )
        if finding.verdict == Verdict.REJECT:
            state.stage = ClaimStage.REJECTED
        return state

    async def _run_parallel_analysis(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        """Run analyst agents sequentially with delays to avoid rate limits."""
        state.stage = ClaimStage.PARALLEL_ANALYSIS
        claim_data = self._agent_claim(state)

        # Run sequentially with delay to respect Groq free-tier rate limits
        for role in PARALLEL_ANALYST_ROLES:
            started = time.perf_counter()
            try:
                # The Risk agent decomposes risk from its peers' findings (incl.
                # detecting ABSTAIN/agent_unavailable). Since analysts run in
                # order with Risk last, its peers are already on state.findings.
                analyze_context = None
                if role == AgentRole.RISK_ASSESSMENT:
                    analyze_context = {
                        "findings": [
                            f.model_dump(mode="json")
                            for f in state.findings
                            if f.agent in PARALLEL_ANALYST_ROLES
                        ]
                    }
                finding = await self._analysts[role].analyze(
                    claim_id=state.claim_id, claim=claim_data, context=analyze_context
                )
                state.findings.append(finding)
                state.decision_path = state.decision_path.append(
                    DecisionStep(
                        agent=role,
                        action="analyzed_claim",
                        summary=finding.reasoning[:100],
                        confidence=finding.confidence,
                    )
                )
                self._log_step(
                    state, role, "analyzed_claim",
                    started=started, status="ok", finding=finding,
                    input_summary="master_form",
                    output_summary=finding.reasoning[:120],
                )
                # Risk agent may publish a decomposed RiskBreakdown on the state.
                self._capture_risk_breakdown(state, role, finding)
            except (LLMAllProvidersFailedError, Exception) as exc:  # noqa: BLE001
                logger.error("Analyst %s failed: %s", role.value, exc)
                finding = self._abstain_finding(role, state.claim_id, exc)
                state.findings.append(finding)
                self._log_step(
                    state, role, "analyzed_claim",
                    started=started, status="error", finding=finding, error=str(exc),
                    input_summary="master_form",
                )
            # Small delay between calls to avoid rate limiting
            await asyncio.sleep(1.5)
        return state

    # ------------------------------------------------------------------
    # Disagreement resolution (debate-only — never decides the outcome)
    # ------------------------------------------------------------------

    def _detect_disagreement(self, state: ClaimWorkflowState) -> bool:
        """True if analyst findings disagree on verdict."""
        analyst_findings = [
            f for f in state.findings if f.agent in PARALLEL_ANALYST_ROLES
        ]
        if len(analyst_findings) < 2:
            return False

        verdicts = {f.verdict for f in analyst_findings}
        # Disagreement: mixed approve/reject, or any flag + approve
        if Verdict.REJECT in verdicts and Verdict.APPROVE in verdicts:
            return True
        if Verdict.FLAG in verdicts and Verdict.APPROVE in verdicts:
            return True
        # Any finding below escalation threshold
        if any(f.confidence.requires_escalation for f in analyst_findings):
            return True
        return False

    async def _resolve_disagreement(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        """Run debate rounds when analysts disagree — EVIDENCE ONLY.

        This stage no longer sets any final verdict and no longer escalates:
        the Judge (``_run_judgment``) is the single decision authority. Debate
        rounds are recorded on ``state.debate_rounds`` purely as evidence
        inputs the Judge may weigh (design §7 / §8.6).
        """
        if not self._detect_disagreement(state):
            return state

        state.stage = ClaimStage.DEBATE
        claim_data = self._agent_claim(state)
        analyst_findings = [
            f for f in state.findings if f.agent in PARALLEL_ANALYST_ROLES
        ]

        for round_num in range(1, MAX_DEBATE_ROUNDS + 1):
            debate_round = DebateRound(
                round_number=round_num, claim_id=state.claim_id
            )
            votes = await asyncio.gather(
                *[
                    self._analysts[role].cast_vote(
                        claim_id=state.claim_id,
                        claim=claim_data,
                        context={
                            "findings": [
                                f.model_dump(mode="json") for f in analyst_findings
                            ]
                        },
                    )
                    for role in PARALLEL_ANALYST_ROLES
                    if role in self._analysts
                ],
                return_exceptions=True,
            )

            for v in votes:
                if not isinstance(v, Exception):
                    debate_round.votes.append(v)

            debate_round.closed_at = now_utc()
            state.debate_rounds.append(debate_round)

            # Stop early once the analysts have clearly converged, but DO NOT
            # record any verdict here — the Judge still rules.
            choices = [v.choice.value for v in debate_round.votes]
            if any(choices.count(c) >= 3 for c in ("approve", "reject", "escalate")):
                break

        return state

    # ------------------------------------------------------------------
    # Judgment — always runs; the single decision authority
    # ------------------------------------------------------------------

    async def _run_judgment(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        """Always run the Judge over findings + blocking conditions.

        Blocking conditions (read off the serialized ``RiskBreakdown``) force a
        REVIEW outcome inside ``rule()``. On a non-empty blocking set or
        ``requires_human_review``, the stage escalates to a human and creates a
        ``HumanEscalation`` record (design §8.6).
        """
        state.stage = ClaimStage.JUDGMENT
        analyst_findings = [
            f for f in state.findings if f.agent in PARALLEL_ANALYST_ROLES
        ]
        blocking = (state.risk_breakdown or {}).get("blocking_conditions", []) or []
        started = time.perf_counter()

        try:
            ruling = await self.judge.rule(
                claim_id=state.claim_id,
                findings=analyst_findings,
                blocking_conditions=blocking,
                debate_history=[
                    dr.model_dump(mode="json") for dr in state.debate_rounds
                ],
                decision_path=state.decision_path,
            )
            self._log_step(
                state, AgentRole.JUDGE, "issued_ruling",
                started=started, status="ok",
                input_summary=f"findings[{len(analyst_findings)}]",
                output_summary=f"verdict={ruling.verdict.value}",
                confidence=ruling.confidence,
            )
        except (LLMAllProvidersFailedError, Exception) as exc:  # noqa: BLE001
            logger.error("Judge failed: %s", exc)
            # The Judge being unavailable must never silently approve — route
            # to REVIEW / human escalation.
            ruling = JudgeRuling(
                claim_id=state.claim_id,
                verdict=Verdict.FLAG,
                confidence=self._confidence(0.3, f"judge unavailable: {exc}"),
                rationale="Judge unavailable; routed to human review.",
                decision_path=state.decision_path,
                requires_human_review=True,
            )
            blocking = [*blocking, "judge_unavailable"]
            finding = self._abstain_finding(AgentRole.JUDGE, state.claim_id, exc)
            state.findings.append(finding)
            self._log_step(
                state, AgentRole.JUDGE, "issued_ruling",
                started=started, status="error", finding=finding, error=str(exc),
                input_summary=f"findings[{len(analyst_findings)}]",
            )

        state.ruling = ruling
        state.decision_path = state.decision_path.append(
            DecisionStep(
                agent=AgentRole.JUDGE,
                action="issued_ruling",
                summary=ruling.rationale[:100],
                confidence=ruling.confidence,
            )
        )

        # Backward-compat for any legacy reader; the authoritative decision is
        # state.ruling.verdict.
        state._consensus_verdict = ruling.verdict  # type: ignore[attr-defined]

        if ruling.requires_human_review or blocking:
            state.stage = ClaimStage.HUMAN_ESCALATION
            reason = (
                EscalationReason.LOW_CONFIDENCE
                if ruling.confidence.requires_escalation
                else EscalationReason.UNRESOLVED_DEBATE
            )
            state.escalation = HumanEscalation(
                claim_id=state.claim_id,
                reason=reason,
                triggered_by=AgentRole.JUDGE,
                confidence_at_escalation=ruling.confidence,
                decision_path=state.decision_path,
            )
        return state

    async def _run_communication(
        self, state: ClaimWorkflowState
    ) -> ClaimWorkflowState:
        """Draft outbound communications from the Judge's final decision."""
        # Always initialize the carrier so /process never reads an unset value.
        state._comm_drafts = {}  # type: ignore[attr-defined]

        if state.stage in (ClaimStage.REJECTED, ClaimStage.FAILED):
            return state

        # The Judge's final decision drives the communications (not a mix of
        # raw analyst reasoning).
        if state.ruling is not None:
            verdict = state.ruling.verdict
            reasoning = state.ruling.rationale
        else:
            verdict = getattr(state, "_consensus_verdict", Verdict.FLAG)
            reasoning = "Claim routed to review."

        human_review = (
            state.stage == ClaimStage.HUMAN_ESCALATION
            or (state.ruling is not None and state.ruling.requires_human_review)
        )
        decision_label = (
            "REVIEW"
            if human_review and verdict != Verdict.REJECT
            else verdict.value
        )

        claim_data = self._agent_claim(state)
        started = time.perf_counter()

        # Don't downgrade an escalation stage; use a working stage marker only
        # when we're on the completion path.
        if not human_review:
            state.stage = ClaimStage.COMMUNICATION

        try:
            drafts = await self.communication.draft(
                claim_id=state.claim_id,
                decision=decision_label,
                reasoning=reasoning[:500],
                claim=claim_data,
            )
            if isinstance(drafts, dict):
                state._comm_drafts = drafts  # type: ignore[attr-defined]
            state.decision_path = state.decision_path.append(
                DecisionStep(
                    agent=AgentRole.COMMUNICATION,
                    action="drafted_communications",
                    summary=f"Decision: {decision_label}",
                )
            )
            self._log_step(
                state, AgentRole.COMMUNICATION, "drafted_communications",
                started=started, status="ok",
                input_summary=f"decision={decision_label}",
                output_summary="drafts_ready",
            )
        except (LLMAllProvidersFailedError, Exception) as exc:  # noqa: BLE001
            logger.error("Communication failed: %s", exc)
            # Leave _comm_drafts as the initialized {} so /process degrades to
            # its default templates.
            finding = self._abstain_finding(
                AgentRole.COMMUNICATION, state.claim_id, exc
            )
            state.findings.append(finding)
            self._log_step(
                state, AgentRole.COMMUNICATION, "drafted_communications",
                started=started, status="error", finding=finding, error=str(exc),
                input_summary=f"decision={decision_label}",
            )

        # Final stage: don't override an escalation.
        if state.stage == ClaimStage.HUMAN_ESCALATION:
            pass
        elif verdict == Verdict.REJECT:
            state.stage = ClaimStage.REJECTED
        else:
            state.stage = ClaimStage.COMPLETED

        state.updated_at = now_utc()
        return state

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_agent_claim(
        self,
        form: Any,
        profile: Any,
        extracted: dict[str, Any],
    ) -> dict[str, Any]:
        """Enriched claim dict threaded to every downstream agent (design §7).

        ``{**form.model_dump(mode="json"), "jurisdiction": profile.model_dump(),
        "raw_extracted": extracted}``. Agents read structured, provenance-tagged
        values but still tolerate the thin legacy shape via ``.get()``.
        """
        agent_claim = form.model_dump(mode="json")
        agent_claim["jurisdiction"] = profile.model_dump()
        agent_claim["raw_extracted"] = extracted
        return agent_claim

    def _agent_claim(self, state: ClaimWorkflowState) -> dict[str, Any]:
        """The enriched claim dict, falling back to the raw extraction."""
        agent_claim = getattr(state, "_agent_claim", None)
        if agent_claim:
            return agent_claim
        return getattr(state, "_extracted_claim", {}) or {}

    def _capture_risk_breakdown(
        self, state: ClaimWorkflowState, role: AgentRole, finding: AgentFinding
    ) -> None:
        """Pull a serialized RiskBreakdown off the Risk agent if it published one.

        The Risk agent (FEAT-003) will attach its decomposed ``RiskBreakdown``;
        until then this is a no-op unless the finding carries one. Kept here so
        ``state.risk_breakdown`` is populated the moment the Risk agent lands.
        """
        if role != AgentRole.RISK_ASSESSMENT:
            return
        rb = getattr(finding, "_risk_breakdown", None)
        if rb is None:
            return
        try:
            state.risk_breakdown = (
                rb.model_dump(mode="json") if hasattr(rb, "model_dump") else dict(rb)
            )
        except Exception:  # noqa: BLE001 - defensive; never fail on telemetry
            logger.debug("Could not capture risk breakdown from %s", role.value)

    @staticmethod
    def _confidence(value: float, rationale: str) -> ConfidenceScore:
        clamped = max(0.0, min(1.0, value))
        return ConfidenceScore(value=clamped, rationale=rationale)

    def _abstain_finding(
        self, role: AgentRole, claim_id: str, exc: Exception
    ) -> AgentFinding:
        """A role-keyed ABSTAIN finding for an unavailable agent (design §14)."""
        return AgentFinding(
            agent=role,
            claim_id=claim_id,
            verdict=Verdict.ABSTAIN,
            confidence=self._confidence(0.3, f"{role.value} unavailable: {exc}"),
            reasoning=(
                f"{role.value} could not complete analysis ({type(exc).__name__})."
            ),
            tags=["agent_unavailable"],
        )

    def _log_step(
        self,
        state: ClaimWorkflowState,
        role: AgentRole,
        action: str,
        *,
        started: float,
        status: str,
        finding: AgentFinding | None = None,
        error: str | None = None,
        input_summary: str = "",
        output_summary: str = "",
        confidence: ConfidenceScore | None = None,
    ) -> None:
        """Append a structured StepLog on ``state._step_logs`` (design §11.1).

        This is the authoritative logs source for ``/process`` (no DB
        dependency). Each row carries the agent display name, action, input/
        output summaries, status, duration, confidence, error, and the
        run's trace id as ``request_id``.
        """
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        conf = confidence or (finding.confidence if finding else None)
        logs: list[dict[str, Any]] = getattr(state, "_step_logs", None)
        if logs is None:
            logs = []
            state._step_logs = logs  # type: ignore[attr-defined]
        logs.append(
            {
                "agent": AGENT_DISPLAY_NAMES.get(role, role.value),
                "agent_role": role.value,
                "action": action,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "status": status,
                "duration_ms": duration_ms,
                "confidence": conf.value if conf else None,
                "error": error,
                "request_id": getattr(self, "_trace_id", None),
            }
        )


__all__ = ["Supervisor", "MAX_DEBATE_ROUNDS"]
