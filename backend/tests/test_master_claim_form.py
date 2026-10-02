"""FEAT-005 unit tests (no live LLM) — Master Claim Form & Judge guards.

Covers design §15: the fixture billing-sum smoke check, TC2 (billing
consistency), TC4 (jurisdiction = IN / NPI not demanded), TC7 (no scalar
auto-approve), TC8 (never auto-reject on missing info), TC9 (conflict
preservation). The real mappers, billing math, jurisdiction inference, and the
Judge ``rule()`` code guard all execute; only the LLM call is mocked.
"""

from __future__ import annotations

import re

import pytest

from agentcore.agents.judge import JudgeAgent
from agentcore.agents.ocr import OCRAgent
from agentcore.agents.risk_assessment import RiskAssessmentAgent
from agentcore.claim_model import (
    BillingFlag,
    ConflictingValue,
    FieldStatus,
    Jurisdiction,
    PolicyStatus,
    field_conflict,
    infer_jurisdiction,
)
from agentcore.llm import AsyncLLMClient
from agentcore.protocol import AgentFinding, AgentRole, Verdict

from tests._pdf_fixture import SYNTHETIC_PDF_TEXT
from tests.conftest import (
    EXPECTED_BILLING_TOTAL,
    SEVEN_BILLING_LINES,
    LLMMock,
    golden_llm_scripts,
)


# ---------------------------------------------------------------------------
# Fixture-fidelity smoke check (design §15 / review finding #5)
# ---------------------------------------------------------------------------


def test_billing_lines_sum_to_total():
    """The seven billing lines in the committed PDF fixture sum to 48760.00."""
    assert len(SEVEN_BILLING_LINES) == 7
    total = round(sum(amount for _name, amount in SEVEN_BILLING_LINES), 2)
    assert total == EXPECTED_BILLING_TOTAL == 48760.00

    # Each itemized line and the TOTAL must literally appear in the extracted
    # fixture text, so the fixture cannot silently drift from the binary.
    for name, amount in SEVEN_BILLING_LINES:
        assert name in SYNTHETIC_PDF_TEXT, f"missing billing line label: {name}"
        assert f"{amount:,.2f}" in SYNTHETIC_PDF_TEXT, f"missing amount: {amount}"
    assert "48,760.00" in SYNTHETIC_PDF_TEXT


# ---------------------------------------------------------------------------
# OCR-driven unit cases (build_master_form, LLM mocked)
# ---------------------------------------------------------------------------


async def _build_form(monkeypatch):
    """Run the real build_master_form on the synthetic PDF with a mocked LLM."""
    LLMMock(golden_llm_scripts()).install(monkeypatch)
    ocr = OCRAgent(role=AgentRole.OCR, llm=AsyncLLMClient())
    form, extracted = await ocr.build_master_form(
        claim_id="unit-claim",
        raw_text=SYNTHETIC_PDF_TEXT,
        source_document="ClaimBlitz_Synthetic_Medical_Claim_Report.pdf",
    )
    return form, extracted


@pytest.mark.asyncio
async def test_tc2_billing_consistency(monkeypatch):
    """TC2 — billing recompute, VERIFIED on a matched submitted total."""
    form, _extracted = await _build_form(monkeypatch)
    billing = form.billing

    assert billing.calculated_total == 48760.0
    assert billing.submitted_total.value == 48760.0
    assert billing.billing_difference == 0
    assert billing.flag == BillingFlag.BILLING_TOTAL_CONSISTENT
    # A deterministic cross-check (not an LLM self-report) upgrades to VERIFIED.
    assert billing.submitted_total.status == FieldStatus.VERIFIED
    assert len(billing.line_items) == 7


@pytest.mark.asyncio
async def test_tc4_jurisdiction_in_npi_not_demanded(monkeypatch):
    """TC4 — IN jurisdiction, NPI not required, NPI MISSING is not a CODING error."""
    form, _extracted = await _build_form(monkeypatch)

    assert form.jurisdiction.jurisdiction == Jurisdiction.IN
    assert form.jurisdiction.npi_required is False
    assert form.provider.npi.status == FieldStatus.MISSING

    # The Validator must not emit a CODING *error* for the missing NPI in IN.
    from agentcore.agents.validator import ValidatorAgent

    agent_claim = form.model_dump(mode="json")
    agent_claim["jurisdiction"] = form.jurisdiction.model_dump()
    validator = ValidatorAgent(role=AgentRole.VALIDATOR, llm=AsyncLLMClient())
    coding = validator._check_coding(agent_claim)

    npi_findings = [c for c in coding if c["field"] == "provider.npi"]
    assert npi_findings, "expected an NPI coding note"
    assert all(c["severity"] != "error" for c in npi_findings)
    assert npi_findings[0]["severity"] == "info"


def test_tc4_infer_jurisdiction_from_fixture():
    """infer_jurisdiction keys IN off the +91 / INR signals in the fixture text."""
    profile = infer_jurisdiction(SYNTHETIC_PDF_TEXT, "INR")
    assert profile.jurisdiction == Jurisdiction.IN
    assert profile.npi_required is False
    assert profile.procedure_coding_required is False


# ---------------------------------------------------------------------------
# Judge code-guard unit cases (TC7 / TC8) — call rule() directly, no Supervisor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tc7_no_scalar_auto_approve(monkeypatch):
    """TC7 — a scripted 'approve' + low risk cannot resurrect APPROVE when a
    blocking condition is present; the in-rule() guard forces REVIEW."""
    scripts = golden_llm_scripts(
        judge={
            "verdict": "approve",
            "confidence": 0.95,
            "reasoning": "Low risk; would approve.",
            "dissenting_agents": [],
            "requires_human_review": False,
        }
    )
    LLMMock(scripts).install(monkeypatch)
    judge = JudgeAgent(role=AgentRole.JUDGE, llm=AsyncLLMClient())

    finding = AgentFinding(
        agent=AgentRole.POLICY_EXPERT,
        claim_id="tc7",
        verdict=Verdict.FLAG,
        confidence=judge.make_confidence(0.9, "x"),
        reasoning="policy missing",
    )
    ruling = await judge.rule(
        claim_id="tc7",
        findings=[finding],
        blocking_conditions=["policy_document_missing"],
    )

    assert ruling.verdict == Verdict.FLAG
    assert ruling.requires_human_review is True


@pytest.mark.asyncio
async def test_tc8_never_auto_reject_on_missing_info(monkeypatch):
    """TC8 — a scripted 'reject' is downgraded to FLAG + human review when the
    only issue is a missing document (never auto-reject on missing info)."""
    scripts = golden_llm_scripts(
        judge={
            "verdict": "reject",
            "confidence": 0.95,
            "reasoning": "Would reject.",
            "dissenting_agents": [],
            "requires_human_review": False,
        }
    )
    LLMMock(scripts).install(monkeypatch)
    judge = JudgeAgent(role=AgentRole.JUDGE, llm=AsyncLLMClient())

    finding = AgentFinding(
        agent=AgentRole.VALIDATOR,
        claim_id="tc8",
        verdict=Verdict.FLAG,
        confidence=judge.make_confidence(0.9, "x"),
        reasoning="identity doc missing",
    )
    ruling = await judge.rule(
        claim_id="tc8",
        findings=[finding],
        blocking_conditions=["identity_document_missing"],
    )

    assert ruling.verdict == Verdict.FLAG
    assert ruling.verdict != Verdict.REJECT
    assert ruling.requires_human_review is True


# ---------------------------------------------------------------------------
# TC9 — conflict preservation + raises documentation risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tc9_conflict_preservation_raises_documentation_risk(monkeypatch):
    """TC9 — two source docs with differing patient DOB -> CONFLICT (both values
    preserved) and the Risk engine raises documentation risk / blocks review."""
    LLMMock(golden_llm_scripts()).install(monkeypatch)

    # Build the golden form, then record a cross-document DOB conflict exactly
    # as the model's conflict factory does (both observed values preserved).
    form, _extracted = await _build_form(monkeypatch)
    form.patient.dob = field_conflict(
        "patient.dob",
        [
            ConflictingValue(
                value="12 February 1992",
                source_document="discharge_summary.pdf",
                confidence=0.9,
            ),
            ConflictingValue(
                value="12 March 1992",
                source_document="identity_card.pdf",
                confidence=0.9,
            ),
        ],
    )

    assert form.patient.dob.status == FieldStatus.CONFLICT
    conflict_values = {c.value for c in form.patient.dob.conflicts}
    assert conflict_values == {"12 February 1992", "12 March 1992"}
    assert "patient.dob" in form.conflict_fields()

    # The Risk engine must register the conflict as a blocking documentation
    # risk (document_conflict), proving it raises review rather than being lost.
    agent_claim = form.model_dump(mode="json")
    agent_claim["jurisdiction"] = form.jurisdiction.model_dump()
    risk = RiskAssessmentAgent(role=AgentRole.RISK_ASSESSMENT, llm=AsyncLLMClient())
    finding = await risk.analyze(claim_id="tc9", claim=agent_claim, context=None)

    breakdown = finding._risk_breakdown  # type: ignore[attr-defined]
    assert "document_conflict" in breakdown.blocking_conditions
    assert breakdown.documentation_risk.blocking is True
