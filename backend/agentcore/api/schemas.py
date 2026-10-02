"""Pydantic request/response schemas for the API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# -- Requests --

class ClaimSubmitRequest(BaseModel):
    raw_text: str = Field(description="Extracted text from the claim document")
    source_filename: str | None = Field(default=None)
    file_meta: dict[str, Any] | None = Field(default=None)


class EscalationResolveRequest(BaseModel):
    resolution_notes: str
    verdict_override: str | None = Field(
        default=None, description="approve|reject|flag or null to keep original"
    )


# -- Responses --

class ProvenanceSummary(BaseModel):
    """Status rollup across every scalar field of the Master Claim Form."""

    extracted: int = 0
    missing: int = 0
    conflict: int = 0
    lowConfidence: int = 0
    verified: int = 0


class ClaimStatusResponse(BaseModel):
    claim_id: str
    stage: str
    final_verdict: str | None = None
    risk_score: float | None = None
    risk_label: str | None = None
    # Extended (design §11): the Judge decision block + provenance rollup for
    # the stored claim. Both are None until the claim has been processed.
    decision: dict[str, Any] | None = None
    provenance_summary: ProvenanceSummary | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MasterFormResponse(BaseModel):
    """Wraps the serialized MasterClaimForm (authoritative schema lives in
    ``claim_model.py``; typed as a dict here to avoid duplicating it)."""

    claim_id: str
    masterClaimForm: dict[str, Any]
    jurisdiction: dict[str, Any] | None = None
    provenanceSummary: ProvenanceSummary | None = None


class DecisionResponse(BaseModel):
    claim_id: str
    decision: dict[str, Any]


class FindingsResponse(BaseModel):
    claim_id: str
    agentFindings: list[dict[str, Any]] = Field(default_factory=list)


class ValidateResponse(BaseModel):
    claim_id: str
    verdict: str
    findings: list[dict[str, Any]] = Field(default_factory=list)


class LogsResponse(BaseModel):
    claim_id: str
    logs: list[dict[str, Any]] = Field(default_factory=list)
    persisted: bool = False


class UploadResponse(BaseModel):
    claim_id: str
    stage: str
    filename: str | None = None
    message: str = "Claim stored; call /claims/{id}/extract or /claims/{id}/process to run."


class ClaimSubmitResponse(BaseModel):
    claim_id: str
    stage: str
    message: str = "Claim submitted for processing"


class WorkflowResponse(BaseModel):
    claim_id: str
    stage: str
    is_paused: bool = False
    retry_count: int = 0
    findings: list[dict[str, Any]] = Field(default_factory=list)
    debate_rounds: list[dict[str, Any]] = Field(default_factory=list)
    ruling: dict[str, Any] | None = None
    escalation: dict[str, Any] | None = None
    decision_path: dict[str, Any] | None = None


class EscalationResponse(BaseModel):
    id: str
    claim_id: str
    reason: str
    triggered_by: str
    confidence_value: float | None = None
    status: str
    assigned_to: str | None = None
    created_at: datetime | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"
    agents_ready: bool = True


class AgentStatusResponse(BaseModel):
    llm_status: dict[str, Any] = Field(default_factory=dict)
    agents: list[str] = Field(default_factory=list)
    pinecone_configured: bool = False
    redis_configured: bool = False
