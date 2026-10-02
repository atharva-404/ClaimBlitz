"""FEAT-005 integration tests — /process end-to-end with the LLM mocked.

Covers design §15: TC1 (golden path), TC3 (policy insufficient evidence),
TC5 (identity document missing), TC6 (fraud: high bill is not fraud), TC10
(graceful degradation), TC-COMM (communication drafts carried out), and
TC-JUDGE1 (always-run Judge on the consensus path).

A ``TestClient`` drives the real ``/process`` handler (which extracts text via
PyMuPDF, falling back to a UTF-8 decode for a non-PDF upload — so uploading the
committed fixture text as bytes feeds the pipeline the exact synthetic-PDF
text). ``AsyncLLMClient.call_json`` is monkeypatched with the marker-keyed
``LLMMock``; everything else (mappers, billing math, jurisdiction, Risk engine,
Judge guard, Communication wiring, /process shape) runs for real and offline.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from agentcore.agents.fraud_detection import NO_EVIDENCE_REASONING
from agentcore.api.app import create_app
from agentcore.claim_model import FieldStatus, PolicyStatus
from agentcore.llm import LLMAllProvidersFailedError

from tests._pdf_fixture import SYNTHETIC_PDF_TEXT
from tests.conftest import LLMMock, golden_llm_scripts

_COVERAGE_TERMS = (
    "insurer_name",
    "start_date",
    "end_date",
    "plan_name",
    "coverage_type",
    "sum_insured",
    "remaining_sum_insured",
    "room_rent_limit",
    "copay",
    "deductible",
    "waiting_period",
    "exclusions",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _fast_pipeline(monkeypatch):
    """Skip the 1.5s inter-stage rate-limit sleeps so integration runs fast.

    This only removes wall-clock delay; the orchestration order and every
    agent call are unchanged.
    """

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


def _post_synthetic(client: TestClient) -> dict:
    """POST the committed synthetic-PDF text through /process and return JSON."""
    files = {
        "file": (
            "ClaimBlitz_Synthetic_Medical_Claim_Report.txt",
            SYNTHETIC_PDF_TEXT.encode("utf-8"),
            "text/plain",
        )
    }
    resp = client.post("/process", files=files)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# TC1 — golden path
# ---------------------------------------------------------------------------


def test_tc1_golden_path(client, monkeypatch):
    LLMMock(golden_llm_scripts()).install(monkeypatch)
    data = _post_synthetic(client)

    assert data["recommendation"] == "REVIEW"
    assert data["decision"]["outcome"] == "REVIEW"

    mf = data["masterClaimForm"]
    assert mf["patient"]["name"]["value"] == "Aarav Mehta"
    assert "pneumonia" in str(mf["clinical"]["primary_diagnosis"]["value"]).lower()
    # Codes are normalized to list[str], trailing description stripped.
    assert mf["clinical"]["diagnosis_codes"]["value"] == ["J18.9"]


# ---------------------------------------------------------------------------
# TC3 — policy insufficient evidence
# ---------------------------------------------------------------------------


def test_tc3_policy_insufficient_evidence(client, monkeypatch):
    LLMMock(golden_llm_scripts()).install(monkeypatch)
    data = _post_synthetic(client)
    mf = data["masterClaimForm"]

    # No policy document -> policy_status MISSING_DOCUMENT.
    assert mf["policy"]["policy_status"] == PolicyStatus.MISSING_DOCUMENT.value

    # Every coverage-term scalar stays MISSING (never invented).
    for term in _COVERAGE_TERMS:
        assert mf["policy"][term]["status"] == FieldStatus.MISSING.value, term

    # Claim-sheet policy_number is allowed to be EXTRACTED (page 3).
    policy_number = mf["policy"]["policy_number"]
    assert policy_number["status"] == FieldStatus.EXTRACTED.value
    assert policy_number["value"] == "DEMO-POL-784215"
    assert policy_number["page"] == 3

    # The Policy agent short-circuits to INSUFFICIENT_EVIDENCE (tagged).
    policy_finding = next(
        f for f in data["agentFindings"] if f["agent"] == "policy_expert"
    )
    assert "coverage_insufficient_evidence" in policy_finding["tags"]
    assert "policy_document_missing" in policy_finding["tags"]

    # Blocking condition surfaced for the Judge.
    assert "policy_document_missing" in data["decision"]["blockingConditions"]
    assert "policy_document_missing" in data["riskBreakdown"]["blocking_conditions"]


# ---------------------------------------------------------------------------
# TC5 — identity document missing
# ---------------------------------------------------------------------------


def test_tc5_identity_document_missing(client, monkeypatch):
    LLMMock(golden_llm_scripts()).install(monkeypatch)
    data = _post_synthetic(client)
    mf = data["masterClaimForm"]

    identity = mf["supporting_documents"]["identity_document"]
    assert identity["present"] is False
    assert identity["status"] == FieldStatus.MISSING.value

    assert "identity_document_missing" in data["decision"]["blockingConditions"]
    assert "identity_document_missing" in data["riskBreakdown"]["blocking_conditions"]


# ---------------------------------------------------------------------------
# TC6 — fraud: no evidence, a high bill is not fraud
# ---------------------------------------------------------------------------


def test_tc6_fraud_amount_only_dropped(client, monkeypatch):
    # Script a single amount-only fraud indicator; the post-filter must drop it.
    scripts = golden_llm_scripts(
        fraud={
            "fraud_indicators": [
                {
                    "indicator": "Claim amount is high",
                    "evidence": "The total bill of INR 48,760 is a large amount.",
                    "confidence": 0.7,
                    "severity": "medium",
                    "risk_type": "BILLING",
                }
            ],
            "overall_fraud_assessment": "High bill.",
            "confidence": 0.7,
        }
    )
    LLMMock(scripts).install(monkeypatch)
    data = _post_synthetic(client)

    fraud = next(f for f in data["agentFindings"] if f["agent"] == "fraud_detection")
    assert fraud["reasoning"] == NO_EVIDENCE_REASONING
    assert fraud["verdict"] == "approve"
    assert "no_fraud_evidence" in fraud["tags"]

    # fraud_risk dimension stays low (band low, not blocking).
    fraud_risk = data["riskBreakdown"]["fraud_risk"]
    assert fraud_risk["band"] == "low"
    assert fraud_risk["blocking"] is False


# ---------------------------------------------------------------------------
# TC10 — graceful degradation
# ---------------------------------------------------------------------------


def test_tc10_graceful_degradation(client, monkeypatch):
    # The Clinical (MEDICAL_EXPERT) analyst's LLM call fails; the pipeline must
    # complete with an ABSTAIN finding + a role-keyed blocking condition.
    scripts = golden_llm_scripts(
        clinical=LLMAllProvidersFailedError({"test": "clinical down"})
    )
    LLMMock(scripts).install(monkeypatch)

    resp = client.post(
        "/process",
        files={
            "file": (
                "synthetic.txt",
                SYNTHETIC_PDF_TEXT.encode("utf-8"),
                "text/plain",
            )
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    clinical = next(
        f for f in data["agentFindings"] if f["agent"] == "medical_expert"
    )
    assert clinical["verdict"] == "abstain"
    assert "agent_unavailable" in clinical["tags"]

    assert "clinical_unavailable" in data["riskBreakdown"]["blocking_conditions"]
    assert data["decision"]["outcome"] == "REVIEW"


# ---------------------------------------------------------------------------
# TC-COMM — communication drafts carried out
# ---------------------------------------------------------------------------


def test_tc_comm_drafts_carried_out(client, monkeypatch):
    email_text = "Your claim is in REVIEW. Additional documents are needed."
    sms_text = "ClaimBlitz: your claim is under review."
    scripts = golden_llm_scripts(
        communication={
            "email_draft": email_text,
            "sms_draft": sms_text,
            "internal_note": "note",
            "tone": "professional",
            "confidence": 0.9,
        }
    )
    LLMMock(scripts).install(monkeypatch)
    data = _post_synthetic(client)

    # /process reads the scripted drafts from state._comm_drafts, not a template.
    assert data["email"] == email_text
    assert data["whatsapp"] == sms_text


# ---------------------------------------------------------------------------
# TC-JUDGE1 — always-run Judge on the consensus path
# ---------------------------------------------------------------------------


def test_tc_judge1_always_run_judge(client, monkeypatch):
    LLMMock(golden_llm_scripts()).install(monkeypatch)
    data = _post_synthetic(client)

    # The decision comes from the Judge ruling (not a majority/consensus
    # fallback): the rationale is the Judge's scripted reasoning, carried
    # through even though the blocking-condition guard forced REVIEW.
    decision = data["decision"]
    assert decision["rationale"] == "Analysts broadly consistent."
    assert data["recommendation"] == "REVIEW"
    # confidence present on the decision proves a ruling object existed.
    assert isinstance(decision["confidence"], (int, float))
    assert decision["confidence"] > 0.0
