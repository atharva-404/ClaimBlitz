"""Risk Assessment Agent — decomposed RiskBreakdown, no scalar override.

Keeps ``AgentRole.RISK_ASSESSMENT`` and the "Risk Assessment Agent" marker and
still returns an ``AgentFinding``. Its ``analyze()`` now computes the six
``RiskDimension`` values deterministically from the Master Claim Form and the
other agents' findings (threaded in via ``context["findings"]``), builds a
``RiskBreakdown`` with role-keyed ``blocking_conditions``, and attaches it to
the returned finding as ``finding._risk_breakdown`` so the Supervisor can
publish it on ``state.risk_breakdown`` (design §8.5 / §14).

Role-keyed blocking conditions for unavailable analysts:
- failed OCR            -> "ocr_unavailable"       (documentation + billing blocking)
- failed Validator      -> "validator_unavailable" (documentation + billing blocking)
- failed Policy         -> "policy_unavailable"    (policy blocking)
- failed Clinical       -> "clinical_unavailable"  (clinical blocking)
- failed Fraud          -> "fraud_unavailable"     (fraud blocking)
Plus evidence-based conditions from the form:
- policy_status != PRESENT       -> "policy_document_missing"
- identity_document not present  -> "identity_document_missing"
- any CONFLICT field             -> "document_conflict"
- billing flag BILLING_MISMATCH  -> "billing_mismatch"

The legacy tags ``risk_<band>`` / ``score_<x>`` are retained for the old
frontend. ``overall_review_risk.band`` collapses a legacy ``critical`` to
``high`` via ``_band_from_score`` (only low|medium|high).
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..claim_model import (
    PolicyStatus,
    RiskBreakdown,
    RiskDimension,
    _band_from_score,
)
from ..protocol import (
    AgentFinding,
    AgentRole,
    Evidence,
    EvidenceSource,
    Verdict,
)


_UNAVAILABLE_TAG = "agent_unavailable"


class RiskAssessmentAgent(Agent):
    """Decomposed risk scoring producing a RiskBreakdown."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Risk Assessment Agent in a medical insurance claim processing "
            "system. You summarize the review risk of a claim across documentation, policy, "
            "clinical, billing, and fraud dimensions.\n\n"
            "The authoritative dimension scores are computed deterministically from the "
            "claim form and the other agents' findings; your narrative explains, it does not "
            "override. A missing field is a documentation risk, never an automatic rejection, "
            "and a high bill amount by itself is not a risk driver.\n\n"
            "Respond with strict JSON:\n"
            '{"reasoning": "risk summary", "confidence": 0.0-1.0, '
            '"notes": ["optional driver notes"]}'
        )

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        peer_findings = _peer_findings(context)

        # Deterministic dimension computation (code owns the scores).
        breakdown = self._compute_breakdown(claim, peer_findings)
        overall = breakdown.overall_review_risk

        # LLM narrative only (never a score source). Best-effort; the finding
        # is still valid if the LLM is unavailable (the Supervisor's wrapper
        # handles an exception, but we also try/except here so a narrative
        # failure does not drop the computed breakdown).
        reasoning = (
            f"Review risk is {overall.band} (score {overall.score:.2f}). "
            + "; ".join(overall.drivers[:4])
        )
        conf_value = 0.7
        try:
            instructions = (
                f"Summarize the review risk for this claim.\n\n"
                f"Computed dimensions:\n"
                f"{json.dumps(breakdown.model_dump(mode='json'), indent=2, default=str)}\n\n"
                f"Explain the drivers in one short paragraph."
            )
            result = await self.ask_llm_json(instructions)
            parsed = result.parsed
            reasoning = parsed.get("reasoning") or reasoning
            conf_value = parsed.get("confidence", conf_value)
        except Exception:  # noqa: BLE001 - narrative is optional; keep the breakdown
            pass

        await self.memory.remember(
            text=f"Claim {claim_id} risk: band={overall.band}, score={overall.score:.2f}",
            metadata={"claim_id": claim_id, "risk_band": overall.band},
        )

        evidence = [
            Evidence(
                source=EvidenceSource.RULE_ENGINE,
                field=dim.name,
                snippet="; ".join(dim.drivers[:3]) or f"{dim.name} {dim.band}",
                weight=dim.score,
            )
            for dim in (
                breakdown.documentation_risk,
                breakdown.policy_risk,
                breakdown.clinical_risk,
                breakdown.billing_risk,
                breakdown.fraud_risk,
            )
            if dim.drivers or dim.blocking
        ]

        # Verdict: a non-empty blocking set means REVIEW -> FLAG; else map band.
        if breakdown.blocking_conditions or overall.band == "high":
            verdict = Verdict.FLAG
        else:
            verdict = Verdict.APPROVE

        finding = AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["billing.flag", "policy.policy_status"],
            # Legacy tags retained for the old frontend (single-token band so
            # risk_<band> never contains an underscore).
            tags=[f"risk_{overall.band}", f"score_{overall.score:.2f}"],
        )
        # Private carrier the Supervisor reads (design §14 risk hook).
        finding._risk_breakdown = breakdown  # type: ignore[attr-defined]
        return finding

    # ------------------------------------------------------------------
    # Deterministic risk decomposition (design §8.5)
    # ------------------------------------------------------------------

    def _compute_breakdown(
        self, claim: dict[str, Any], peer_findings: list[AgentFinding]
    ) -> RiskBreakdown:
        unavailable = _unavailable_roles(peer_findings)
        blocking_conditions: list[str] = []

        # --- documentation_risk ---
        doc_drivers: list[str] = []
        doc_blocking = False
        missing_required = _count_missing_required(claim)
        doc_score = min(0.9, 0.1 + 0.08 * missing_required)
        if missing_required:
            doc_drivers.append(f"{missing_required} required field(s) MISSING")

        docs = claim.get("supporting_documents") or {}
        if not _doc_present(docs, "policy_document"):
            doc_score = max(doc_score, 0.7)
            doc_drivers.append("policy_document_missing")
            if "policy_document_missing" not in blocking_conditions:
                blocking_conditions.append("policy_document_missing")
        if not _doc_present(docs, "identity_document"):
            doc_score = max(doc_score, 0.7)
            doc_blocking = True
            doc_drivers.append("identity_document_missing")
            if "identity_document_missing" not in blocking_conditions:
                blocking_conditions.append("identity_document_missing")

        if _has_conflict(claim):
            doc_score = max(doc_score, 0.8)
            doc_blocking = True
            doc_drivers.append("document_conflict")
            if "document_conflict" not in blocking_conditions:
                blocking_conditions.append("document_conflict")

        # --- billing_risk ---
        bill_drivers: list[str] = []
        bill_blocking = False
        billing = claim.get("billing") or {}
        flag = billing.get("flag")
        if flag == "BILLING_MISMATCH":
            bill_score = 0.75
            bill_blocking = True
            bill_drivers.append("billing_mismatch")
            if "billing_mismatch" not in blocking_conditions:
                blocking_conditions.append("billing_mismatch")
        elif flag == "BILLING_TOTAL_CONSISTENT":
            bill_score = 0.1
            bill_drivers.append("billing_total_consistent")
        else:
            bill_score = 0.4
            bill_drivers.append("billing_insufficient_data")

        # --- policy_risk ---
        pol_drivers: list[str] = []
        pol_blocking = False
        policy_status = (claim.get("policy") or {}).get("policy_status")
        if policy_status != PolicyStatus.PRESENT.value:
            pol_score = 0.7
            pol_blocking = True
            pol_drivers.append(f"policy_status={policy_status}")
        else:
            pol_score = 0.15
            pol_drivers.append("policy_present")

        # --- clinical_risk --- (from Clinical Consistency findings)
        clin_drivers: list[str] = []
        clin_score, clin_inconsistent = _finding_signal(
            peer_findings, AgentRole.MEDICAL_EXPERT
        )
        if clin_inconsistent:
            clin_drivers.append("clinical_inconsistency")

        # --- fraud_risk --- (from surviving fraud indicators)
        fraud_drivers: list[str] = []
        fraud_score, fraud_flagged = _finding_signal(
            peer_findings, AgentRole.FRAUD_DETECTION
        )
        if fraud_flagged:
            fraud_drivers.append("fraud_indicator")
        else:
            fraud_drivers.append("no_fraud_evidence")

        # --- unavailable analysts -> role-keyed blocking conditions ---
        for role in unavailable:
            if role == AgentRole.OCR:
                _add(blocking_conditions, "ocr_unavailable")
                doc_blocking = True
                bill_blocking = True
                doc_drivers.append("ocr_unavailable")
                bill_drivers.append("ocr_unavailable")
                doc_score = max(doc_score, 0.8)
                bill_score = max(bill_score, 0.8)
            elif role == AgentRole.VALIDATOR:
                _add(blocking_conditions, "validator_unavailable")
                doc_blocking = True
                bill_blocking = True
                doc_drivers.append("validator_unavailable")
                bill_drivers.append("validator_unavailable")
                doc_score = max(doc_score, 0.8)
                bill_score = max(bill_score, 0.8)
            elif role == AgentRole.POLICY_EXPERT:
                _add(blocking_conditions, "policy_unavailable")
                pol_blocking = True
                pol_drivers.append("policy_unavailable")
                pol_score = max(pol_score, 0.8)
            elif role == AgentRole.MEDICAL_EXPERT:
                _add(blocking_conditions, "clinical_unavailable")
                clin_drivers.append("clinical_unavailable")
                clin_score = max(clin_score, 0.8)
            elif role == AgentRole.FRAUD_DETECTION:
                _add(blocking_conditions, "fraud_unavailable")
                fraud_drivers.append("fraud_unavailable")
                fraud_score = max(fraud_score, 0.8)

        documentation_risk = _dim("documentation", doc_score, doc_drivers, doc_blocking)
        policy_risk = _dim("policy", pol_score, pol_drivers, pol_blocking)
        clinical_risk = _dim("clinical", clin_score, clin_drivers, clin_inconsistent)
        billing_risk = _dim("billing", bill_score, bill_drivers, bill_blocking)
        fraud_risk = _dim("fraud", fraud_score, fraud_drivers, False)

        # Overall is display-only: max of the dimensions (explainable), with the
        # band collapsing a legacy 'critical' into 'high' via _band_from_score.
        overall_score = max(
            documentation_risk.score,
            policy_risk.score,
            clinical_risk.score,
            billing_risk.score,
            fraud_risk.score,
        )
        overall_blocking = bool(blocking_conditions)
        overall_drivers = list(dict.fromkeys(blocking_conditions)) or ["no_blocking_conditions"]
        overall_review_risk = _dim(
            "overall_review", overall_score, overall_drivers, overall_blocking
        )

        return RiskBreakdown(
            documentation_risk=documentation_risk,
            policy_risk=policy_risk,
            clinical_risk=clinical_risk,
            billing_risk=billing_risk,
            fraud_risk=fraud_risk,
            overall_review_risk=overall_review_risk,
            blocking_conditions=list(dict.fromkeys(blocking_conditions)),
        )


# ---------------------------------------------------------------------------
# Module-level helpers (deterministic)
# ---------------------------------------------------------------------------


def _dim(name: str, score: float, drivers: list[str], blocking: bool) -> RiskDimension:
    clamped = max(0.0, min(1.0, round(score, 4)))
    return RiskDimension(
        name=name,
        score=clamped,
        band=_band_from_score(clamped),
        drivers=list(dict.fromkeys(drivers)),
        blocking=blocking,
    )


def _add(conditions: list[str], condition: str) -> None:
    if condition not in conditions:
        conditions.append(condition)


def _peer_findings(context: dict[str, Any] | None) -> list[AgentFinding]:
    """Parse peer findings from context, tolerating dicts or AgentFinding."""
    if not context:
        return []
    raw = context.get("findings") or context.get("peer_findings") or []
    out: list[AgentFinding] = []
    for f in raw:
        if isinstance(f, AgentFinding):
            out.append(f)
        elif isinstance(f, dict):
            try:
                out.append(AgentFinding.model_validate(f))
            except Exception:  # noqa: BLE001
                continue
    return out


def _unavailable_roles(peer_findings: list[AgentFinding]) -> set[AgentRole]:
    """Roles whose finding is ABSTAIN tagged agent_unavailable."""
    roles: set[AgentRole] = set()
    for f in peer_findings:
        if f.verdict == Verdict.ABSTAIN and _UNAVAILABLE_TAG in (f.tags or []):
            roles.add(f.agent)
    return roles


def _finding_signal(
    peer_findings: list[AgentFinding], role: AgentRole
) -> tuple[float, bool]:
    """Return (risk_score, flagged) derived from a peer finding's verdict.

    FLAG/REJECT -> elevated risk; APPROVE -> low; ABSTAIN or absent -> moderate.
    """
    for f in peer_findings:
        if f.agent != role:
            continue
        if f.verdict in (Verdict.FLAG, Verdict.REJECT):
            return 0.6, True
        if f.verdict == Verdict.APPROVE:
            return 0.1, False
        return 0.4, False  # ABSTAIN
    return 0.3, False  # absent


def _count_missing_required(claim: dict[str, Any]) -> int:
    """Count MISSING scalars in the core sections (jurisdiction-light proxy)."""
    count = 0
    for section_name in ("patient", "clinical", "hospitalization"):
        section = claim.get(section_name)
        if not isinstance(section, dict):
            continue
        for cell in section.values():
            if isinstance(cell, dict) and cell.get("status") == "MISSING":
                count += 1
    return count


def _doc_present(docs: dict[str, Any], name: str) -> bool:
    entry = docs.get(name)
    return isinstance(entry, dict) and bool(entry.get("present"))


def _has_conflict(claim: dict[str, Any]) -> bool:
    for section in claim.values():
        if not isinstance(section, dict):
            continue
        for cell in section.values():
            if isinstance(cell, dict) and cell.get("status") == "CONFLICT":
                return True
    return False


__all__ = ["RiskAssessmentAgent"]
