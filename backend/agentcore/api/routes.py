"""API route definitions for the multi-agent claim system.

The single ``router`` below is mounted twice by ``app.py`` (prefix ``/v2`` and
``""``), so every handler is live at both ``/<path>`` and ``/v2/<path>``. This
is intentional (design §11): the frontend calls the root ``/process`` while
everything else uses ``/v2``. New handlers are registered **once** on this
``router`` — there is exactly one handler per route, two mount paths.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from ..claim_model import FieldStatus
from ..protocol import AgentRole, ClaimStage, Verdict, new_id
from .deps import get_supervisor_dep, get_blackboard_dep
from .schemas import (
    AgentStatusResponse,
    ClaimStatusResponse,
    ClaimSubmitRequest,
    ClaimSubmitResponse,
    DecisionResponse,
    EscalationResolveRequest,
    EscalationResponse,
    FindingsResponse,
    HealthResponse,
    LogsResponse,
    MasterFormResponse,
    ProvenanceSummary,
    UploadResponse,
    ValidateResponse,
    WorkflowResponse,
)

router = APIRouter()


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()


@router.get("/health/agents", response_model=AgentStatusResponse)
async def agent_status() -> AgentStatusResponse:
    return AgentStatusResponse(
        agents=[r.value for r in AgentRole],
        pinecone_configured=True,
        redis_configured=True,
    )


# --------------------------------------------------------------------------
# Claims
# --------------------------------------------------------------------------


@router.post("/claims", response_model=ClaimSubmitResponse, status_code=202)
async def submit_claim(
    req: ClaimSubmitRequest,
    background_tasks: BackgroundTasks,
) -> ClaimSubmitResponse:
    """Submit a new claim for multi-agent processing.

    Processing runs in a background task so the endpoint returns
    immediately with a claim_id the client can poll.
    """
    claim_id = new_id()
    blackboard = get_blackboard_dep()

    # Store initial state on blackboard for immediate status queries
    await blackboard.set_many(claim_id, {
        "stage": ClaimStage.INGESTED.value,
        "source_filename": req.source_filename,
        "raw_text": req.raw_text,
        "file_meta": req.file_meta or {},
    })

    # Kick off async processing
    background_tasks.add_task(
        _process_claim_background,
        claim_id=claim_id,
        raw_text=req.raw_text,
        file_meta=req.file_meta or {},
    )

    return ClaimSubmitResponse(
        claim_id=claim_id,
        stage=ClaimStage.INGESTED.value,
    )


async def _process_claim_background(
    *, claim_id: str, raw_text: str, file_meta: dict[str, Any]
) -> None:
    """Run the full Supervisor pipeline in the background."""
    supervisor = get_supervisor_dep()
    blackboard = get_blackboard_dep()

    try:
        state = await supervisor.process_claim(
            claim_id=claim_id,
            raw_text=raw_text,
            file_meta=file_meta,
        )
        # Update blackboard with final state (incl. the canonical response so
        # the GET endpoints can serve it without re-running the pipeline).
        response = _build_process_response(state, raw_text, claim_id)
        await blackboard.set_many(claim_id, {
            "stage": state.stage.value,
            "final_verdict": getattr(state, "_consensus_verdict", None)
            and getattr(state, "_consensus_verdict").value,
            "findings_count": len(state.findings),
            "decision_steps": len(state.decision_path.steps),
            "process_response": response,
            "raw_text": raw_text,
            "file_meta": file_meta,
        })
        await blackboard.publish_event(claim_id, {
            "type": "processing_complete",
            "stage": state.stage.value,
        })
    except Exception as exc:
        await blackboard.set_many(claim_id, {
            "stage": ClaimStage.FAILED.value,
            "error": str(exc),
        })
        await blackboard.publish_event(claim_id, {
            "type": "processing_failed",
            "error": str(exc),
        })


@router.get("/claims/{claim_id}", response_model=ClaimStatusResponse)
async def get_claim_status(claim_id: str) -> ClaimStatusResponse:
    """Get current status of a claim.

    Extended (design §11) with the Judge ``decision`` block and the
    ``provenance_summary`` rollup when the claim has been processed.
    """
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")

    response = data.get("process_response") or {}
    decision = response.get("decision")
    prov = response.get("provenanceSummary")
    risk = response.get("riskBreakdown") or {}
    overall = risk.get("overall_review_risk") or {}

    return ClaimStatusResponse(
        claim_id=claim_id,
        stage=data.get("stage", "unknown"),
        final_verdict=data.get("final_verdict"),
        risk_score=response.get("riskScore", overall.get("score")),
        risk_label=response.get("riskLabel", overall.get("band")),
        decision=decision,
        provenance_summary=ProvenanceSummary(**prov) if prov else None,
    )


@router.get("/claims/{claim_id}/workflow", response_model=WorkflowResponse)
async def get_claim_workflow(claim_id: str) -> WorkflowResponse:
    """Get full workflow state including findings, debate, and ruling."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    return WorkflowResponse(
        claim_id=claim_id,
        stage=data.get("stage", "unknown"),
        findings=data.get("findings", []),
        debate_rounds=data.get("debate_rounds", []),
        ruling=data.get("ruling"),
        decision_path=data.get("decision_path"),
    )


@router.post("/claims/{claim_id}/pause")
async def pause_claim(claim_id: str) -> dict[str, str]:
    """Pause processing of a claim."""
    blackboard = get_blackboard_dep()
    await blackboard.set_field(claim_id, "is_paused", True)
    return {"claim_id": claim_id, "status": "paused"}


@router.post("/claims/{claim_id}/resume")
async def resume_claim(claim_id: str) -> dict[str, str]:
    """Resume a paused claim."""
    blackboard = get_blackboard_dep()
    await blackboard.set_field(claim_id, "is_paused", False)
    return {"claim_id": claim_id, "status": "resumed"}


@router.post("/claims/{claim_id}/retry")
async def retry_claim(
    claim_id: str, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Retry a failed claim from the beginning."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    if data.get("stage") != ClaimStage.FAILED.value:
        raise HTTPException(
            status_code=400, detail="Only failed claims can be retried"
        )
    await blackboard.set_field(claim_id, "stage", ClaimStage.INGESTED.value)

    raw_text = data.get("raw_text", "")
    file_meta = data.get("file_meta", {})
    background_tasks.add_task(
        _process_claim_background,
        claim_id=claim_id,
        raw_text=raw_text,
        file_meta=file_meta,
    )
    return {"claim_id": claim_id, "status": "retrying"}


# --------------------------------------------------------------------------
# New claim endpoints (design §11) — stored-claim lifecycle. Each handler is
# registered once on `router`, so each is live at both /<path> and /v2/<path>.
# --------------------------------------------------------------------------


@router.post("/claims/upload", response_model=UploadResponse, status_code=201)
async def upload_claim(file: UploadFile = File(...)) -> UploadResponse:
    """Store an uploaded document + its extracted text; do NOT run the pipeline.

    ``POST /process`` remains the single upload-and-run path. This endpoint only
    stores the claim so a later ``/claims/{id}/extract`` or
    ``/claims/{id}/process`` can act on it.
    """
    content = await file.read()
    raw_text = _extract_text(content)
    if not raw_text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract text from uploaded file"
        )

    claim_id = new_id()
    blackboard = get_blackboard_dep()
    await blackboard.set_many(claim_id, {
        "stage": ClaimStage.INGESTED.value,
        "source_filename": file.filename,
        "raw_text": raw_text,
        "file_meta": {"filename": file.filename, "size_kb": len(content) // 1024},
    })
    return UploadResponse(
        claim_id=claim_id,
        stage=ClaimStage.INGESTED.value,
        filename=file.filename,
    )


@router.post("/claims/{claim_id}/extract", response_model=MasterFormResponse)
async def extract_claim(claim_id: str) -> MasterFormResponse:
    """Run Scanner + OCR only on a stored claim; persist and return the form."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")

    raw_text = data.get("raw_text", "")
    file_meta = data.get("file_meta", {})
    supervisor = get_supervisor_dep()

    source_document = file_meta.get("filename")
    try:
        form, extracted = await supervisor.ocr.build_master_form(
            claim_id=claim_id,
            raw_text=raw_text,
            source_document=source_document,
        )
        master_form = form.model_dump(mode="json")
        prov = _provenance_summary(form)
    except Exception:  # noqa: BLE001 - degrade to the all-MISSING baseline
        from ..claim_model import build_empty_master_form, infer_jurisdiction

        profile = infer_jurisdiction(raw_text, None)
        form = build_empty_master_form(claim_id, profile)
        master_form = form.model_dump(mode="json")
        prov = _provenance_summary(form)

    await blackboard.set_many(claim_id, {
        "stage": ClaimStage.OCR_EXTRACTION.value,
        "master_form": master_form,
    })

    return MasterFormResponse(
        claim_id=claim_id,
        masterClaimForm=master_form,
        jurisdiction=master_form.get("jurisdiction"),
        provenanceSummary=prov,
    )


@router.get("/claims/{claim_id}/master-form", response_model=MasterFormResponse)
async def get_master_form(claim_id: str) -> MasterFormResponse:
    """Return the stored Master Claim Form; 404 if not extracted yet."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")

    master_form = data.get("master_form")
    if master_form is None:
        response = data.get("process_response") or {}
        master_form = response.get("masterClaimForm")
    if master_form is None:
        raise HTTPException(
            status_code=404, detail="Master Claim Form not extracted yet"
        )

    return MasterFormResponse(
        claim_id=claim_id,
        masterClaimForm=master_form,
        jurisdiction=master_form.get("jurisdiction"),
        provenanceSummary=_provenance_summary_from_dict(master_form),
    )


@router.post("/claims/{claim_id}/validate", response_model=ValidateResponse)
async def validate_claim(claim_id: str) -> ValidateResponse:
    """Run the Validator against the stored (or freshly extracted) form."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")

    supervisor = get_supervisor_dep()
    master_form = data.get("master_form")
    raw_text = data.get("raw_text", "")
    file_meta = data.get("file_meta", {})

    # Build the enriched agent-claim the Validator expects. Prefer a stored
    # master_form; otherwise extract once now.
    if master_form is None:
        form, extracted = await supervisor.ocr.build_master_form(
            claim_id=claim_id,
            raw_text=raw_text,
            source_document=file_meta.get("filename"),
        )
        master_form = form.model_dump(mode="json")
        await blackboard.set_field(claim_id, "master_form", master_form)
    else:
        extracted = {}

    agent_claim = dict(master_form)
    agent_claim["jurisdiction"] = master_form.get("jurisdiction")
    agent_claim["raw_extracted"] = extracted

    try:
        finding = await supervisor.validator.analyze(
            claim_id=claim_id, claim=agent_claim
        )
    except Exception as exc:  # noqa: BLE001 - degrade; never 500 on LLM failure
        finding = supervisor._abstain_finding(AgentRole.VALIDATOR, claim_id, exc)

    return ValidateResponse(
        claim_id=claim_id,
        verdict=finding.verdict.value,
        findings=[finding.model_dump(mode="json")],
    )


@router.post("/claims/{claim_id}/process")
async def process_stored_claim(claim_id: str) -> dict:
    """Run the full pipeline synchronously on an already-stored claim.

    Returns the canonical §10 shape (distinct from ``/process`` which runs on an
    uploaded file).
    """
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")

    raw_text = data.get("raw_text", "")
    file_meta = data.get("file_meta", {})
    return await _run_and_store(claim_id, raw_text, file_meta)


@router.post("/claims/{claim_id}/reprocess")
async def reprocess_claim(claim_id: str) -> dict:
    """Re-run the full pipeline on a stored claim (synchronous)."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")

    raw_text = data.get("raw_text", "")
    file_meta = data.get("file_meta", {})
    return await _run_and_store(claim_id, raw_text, file_meta)


@router.get("/claims/{claim_id}/findings", response_model=FindingsResponse)
async def get_claim_findings(claim_id: str) -> FindingsResponse:
    """Return the full agent findings for a processed claim."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    response = data.get("process_response") or {}
    return FindingsResponse(
        claim_id=claim_id,
        agentFindings=response.get("agentFindings", []),
    )


@router.get("/claims/{claim_id}/decision", response_model=DecisionResponse)
async def get_claim_decision(claim_id: str) -> DecisionResponse:
    """Return the Judge's decision block for a processed claim."""
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    response = data.get("process_response") or {}
    decision = response.get("decision")
    if decision is None:
        raise HTTPException(status_code=404, detail="Claim not processed yet")
    return DecisionResponse(claim_id=claim_id, decision=decision)


@router.get("/claims/{claim_id}/logs", response_model=LogsResponse)
async def get_claim_logs(claim_id: str) -> LogsResponse:
    """Return structured step logs.

    Uses the persisted audit trail (``AuditRepository.get_trail``) when
    available; otherwise falls back to the in-run ``state._step_logs`` captured
    in the stored response and sets ``persisted=false`` (design §11.1).
    """
    blackboard = get_blackboard_dep()
    data = await blackboard.get_all(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Try the persisted audit trail first; fall back to in-run logs when Mongo
    # is unavailable (AuditRepository.__init__ reaches for get_database()).
    try:
        from ..db.repos import AuditRepository

        repo = AuditRepository()
        trail = await repo.get_trail(claim_id)
        if trail:
            return LogsResponse(claim_id=claim_id, logs=trail, persisted=True)
    except Exception:  # noqa: BLE001 - Mongo unavailable -> in-memory fallback
        pass

    response = data.get("process_response") or {}
    return LogsResponse(
        claim_id=claim_id,
        logs=response.get("logs", []),
        persisted=False,
    )


# --------------------------------------------------------------------------
# Escalations
# --------------------------------------------------------------------------


@router.get("/escalations", response_model=list[EscalationResponse])
async def list_escalations() -> list[EscalationResponse]:
    """List pending human escalations."""
    # Placeholder: in production this would query Postgres via repos
    return []


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str, req: EscalationResolveRequest
) -> dict[str, str]:
    """Resolve a human escalation."""
    # Placeholder: would update Postgres + trigger communication agent
    return {
        "escalation_id": escalation_id,
        "status": "resolved",
        "notes": req.resolution_notes,
    }


# --------------------------------------------------------------------------
# Legacy-compatible /process endpoint (what the frontend calls directly)
# --------------------------------------------------------------------------


@router.post("/process")
async def process_file_upload(file: UploadFile = File(...)) -> dict:
    """Process a claim document upload — frontend-compatible endpoint.

    Accepts a PDF/image file, extracts text, runs the full Supervisor pipeline
    synchronously, and returns the canonical §10 shape (every legacy key the
    frontend reads plus the new canonical blocks).
    """
    content = await file.read()
    raw_text = _extract_text(content)
    if not raw_text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract text from uploaded file"
        )

    claim_id = new_id()
    return await _run_and_store(
        claim_id,
        raw_text,
        {"filename": file.filename, "size_kb": len(content) // 1024},
    )


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _extract_text(content: bytes) -> str:
    """Extract text from an uploaded file; fall back to a plain-text decode."""
    import fitz  # PyMuPDF

    raw_text = ""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        for page in doc:
            raw_text += page.get_text()
        doc.close()
    except Exception:  # noqa: BLE001 - not a PDF -> treat as plain text
        raw_text = content.decode("utf-8", errors="ignore")
    return raw_text


async def _run_and_store(
    claim_id: str, raw_text: str, file_meta: dict[str, Any]
) -> dict:
    """Run the full pipeline synchronously and persist the canonical response."""
    supervisor = get_supervisor_dep()
    blackboard = get_blackboard_dep()

    state = await supervisor.process_claim(
        claim_id=claim_id,
        raw_text=raw_text,
        file_meta=file_meta,
    )
    response = _build_process_response(state, raw_text, claim_id)
    await blackboard.set_many(claim_id, {
        "stage": state.stage.value,
        "final_verdict": response["recommendation"],
        "master_form": state.master_form,
        "process_response": response,
        "raw_text": raw_text,
        "file_meta": file_meta,
    })
    return response


def _recommendation_from_ruling(state: Any) -> tuple[str, bool, list[str]]:
    """Derive (recommendation, requires_human, blocking_conditions) from the
    Judge ruling only — no risk-based override, no majority-vote fallback
    (design §9).
    """
    blocking = list((state.risk_breakdown or {}).get("blocking_conditions", []) or [])
    ruling = state.ruling
    if ruling is None:
        return "REVIEW", True, blocking + ["judge_unavailable"]

    recommendation = {
        Verdict.APPROVE: "APPROVE",
        Verdict.REJECT: "REJECT",
    }.get(ruling.verdict, "REVIEW")
    if ruling.requires_human_review:
        recommendation = "REVIEW"
    requires_human = ruling.requires_human_review or recommendation == "REVIEW"
    return recommendation, requires_human, blocking


def _claim_data_adapter(master_form: dict[str, Any]) -> dict[str, Any]:
    """Null-safe legacy ``claimData`` derived from the Master Claim Form.

    MISSING fields map to ``None``/empty, never raise (design §10).
    """
    mf = master_form or {}

    def cell(section: str, field: str) -> Any:
        return (mf.get(section) or {}).get(field, {}) or {}

    def val(section: str, field: str) -> Any:
        return cell(section, field).get("value")

    def first(section: str, field: str) -> Any:
        raw = val(section, field)
        return (raw or [None])[0] if isinstance(raw, list) else (raw or None)

    procedures = (mf.get("procedures") or {}).get("items") or []
    cpt_code = None
    if procedures:
        cpt_code = ((procedures[0] or {}).get("code") or {}).get("value")

    return {
        "patientName": val("patient", "name"),
        "diagnosis": val("clinical", "primary_diagnosis"),
        "diagnosisCode": first("clinical", "diagnosis_codes"),
        "cptCode": cpt_code,
        "provider": val("provider", "hospital_name"),
        "totalBilled": val("billing", "submitted_total") or 0,
        "dateOfService": val("hospitalization", "admission_date"),
    }


def _provenance_summary(form: Any) -> ProvenanceSummary:
    """Status rollup across every scalar FieldProvenance of a MasterClaimForm."""
    counts = {s: 0 for s in (
        FieldStatus.EXTRACTED, FieldStatus.MISSING, FieldStatus.CONFLICT,
        FieldStatus.LOW_CONFIDENCE, FieldStatus.VERIFIED,
    )}
    for f in form.all_fields():
        if f.status in counts:
            counts[f.status] += 1
    return ProvenanceSummary(
        extracted=counts[FieldStatus.EXTRACTED],
        missing=counts[FieldStatus.MISSING],
        conflict=counts[FieldStatus.CONFLICT],
        lowConfidence=counts[FieldStatus.LOW_CONFIDENCE],
        verified=counts[FieldStatus.VERIFIED],
    )


def _provenance_summary_from_dict(master_form: dict[str, Any]) -> ProvenanceSummary:
    """Rollup over a serialized master_form dict (every scalar is a provenance
    cell with a ``status`` key)."""
    counts = {
        "EXTRACTED": 0, "MISSING": 0, "CONFLICT": 0,
        "LOW_CONFIDENCE": 0, "VERIFIED": 0,
    }

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            status = node.get("status")
            if isinstance(status, str) and status in counts and "field" in node:
                counts[status] += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(master_form)
    return ProvenanceSummary(
        extracted=counts["EXTRACTED"],
        missing=counts["MISSING"],
        conflict=counts["CONFLICT"],
        lowConfidence=counts["LOW_CONFIDENCE"],
        verified=counts["VERIFIED"],
    )


def _build_process_response(state: Any, raw_text: str, claim_id: str) -> dict:
    """Build the canonical §10 ``/process`` response.

    Every legacy key the frontend reads is preserved; the new canonical blocks
    are added. The recommendation comes only from ``state.ruling`` (design §9);
    risk score/label are read from ``state.risk_breakdown`` (never tag-split).
    """
    master_form = state.master_form or {}
    risk_breakdown = state.risk_breakdown or {}
    overall = risk_breakdown.get("overall_review_risk") or {}

    recommendation, requires_human, blocking = _recommendation_from_ruling(state)

    # Risk score/label from the breakdown (design §8.5/§10). When the Risk agent
    # degraded (no breakdown) default to 0.0 / "MEDIUM" and rely on the Judge.
    if overall:
        risk_score = float(overall.get("score", 0.0))
        risk_label = str(overall.get("band", "medium")).upper()
    else:
        risk_score = 0.0
        risk_label = "MEDIUM"

    # Communication drafts from state._comm_drafts (template fallback only).
    comm_drafts = getattr(state, "_comm_drafts", {}) or {}
    email_draft = comm_drafts.get("email_draft") or (
        f"Subject: Claim {claim_id} - {recommendation}\n\n"
        f"Dear Policyholder,\n\nYour claim has been processed.\n"
        f"Decision: {recommendation}\nRisk Level: {risk_label}\n\n"
        f"Best regards,\nClaimBlitz AI"
    )
    whatsapp_draft = comm_drafts.get("sms_draft") or (
        f"Claim Update: {recommendation} | Risk: {risk_label} ({risk_score:.2f})"
    )

    # Risk reasons: prefer the overall-risk drivers, else analyst reasoning.
    risk_reasons = list(overall.get("drivers", []) or [])
    if not risk_reasons:
        risk_reasons = [
            f.reasoning
            for f in state.findings
            if f.agent in (AgentRole.FRAUD_DETECTION, AgentRole.RISK_ASSESSMENT)
        ]

    ruling = state.ruling
    decision = {
        "outcome": recommendation,
        "requiresHumanReview": requires_human,
        "confidence": ruling.confidence.value if ruling else 0.0,
        "rationale": ruling.rationale if ruling else "Judge unavailable; routed to human review.",
        "blockingConditions": blocking,
        "basis": [
            {"source": f.agent.value, "evidence": f.reasoning}
            for f in state.findings
            if f.agent in (AgentRole.POLICY_EXPERT, AgentRole.FRAUD_DETECTION, AgentRole.VALIDATOR)
        ],
    }

    # Debate: real rounds only (design §12).
    debate_rounds = [dr.model_dump(mode="json") for dr in state.debate_rounds]
    debate = {"occurred": bool(debate_rounds), "rounds": debate_rounds}

    jurisdiction = master_form.get("jurisdiction") or {}

    return {
        # --- legacy keys preserved ---
        "claimData": _claim_data_adapter(master_form),
        "riskScore": risk_score,
        "riskLabel": risk_label,
        "recommendation": recommendation,
        "riskReasons": risk_reasons,
        "extractionIssues": _extraction_issues(state),
        "extractionTextPreview": raw_text[:500],
        "riskModel": {
            "engine": "multi-agent",
            "modelName": "claimblitz-9-agent-v2",
            "baseScore": 0.1,
            "maxIssuePenalty": 0.5,
            "issuePenaltyPerItem": 0.1,
            "thresholds": {"lowMax": 0.3, "mediumMax": 0.6, "highMax": 1.0},
            "contributions": [
                {
                    "rule": f.agent.value,
                    "delta": 1 - f.confidence.value,
                    "reason": f.reasoning[:80],
                }
                for f in state.findings
                if f.agent in (
                    AgentRole.FRAUD_DETECTION,
                    AgentRole.RISK_ASSESSMENT,
                    AgentRole.MEDICAL_EXPERT,
                )
            ],
        },
        "email": email_draft,
        "whatsapp": whatsapp_draft,
        "findings": [
            {
                "agent": f.agent.value,
                "verdict": f.verdict.value,
                "confidence": f.confidence.value,
                "reasoning": f.reasoning[:100],
            }
            for f in state.findings
        ],
        "stage": state.stage.value,
        "decisionSteps": len(state.decision_path.steps),

        # --- new canonical blocks (design §10) ---
        "masterClaimForm": master_form,
        "riskBreakdown": risk_breakdown,
        "decision": decision,
        "provenanceSummary": _provenance_summary_from_dict(master_form).model_dump(),
        "agentFindings": [f.model_dump(mode="json") for f in state.findings],
        "debate": debate,
        "logs": getattr(state, "_step_logs", []) or [],
        "jurisdiction": jurisdiction,
    }


def _extraction_issues(state: Any) -> list[str]:
    """Dotted paths of MISSING fields on the master form (null-safe)."""
    extracted = getattr(state, "_extracted_claim", {}) or {}
    issues = extracted.get("missing_fields")
    if isinstance(issues, list):
        return issues
    return []
