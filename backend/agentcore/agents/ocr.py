"""OCR Agent — structured field extraction + Master Claim Form population.

Takes raw text (from a PDF parser or actual OCR) and uses LLM reasoning to
read the structured claim fields that literally appear in the document. The
LLM is used **only to read values present in the text** — code (not the LLM)
assigns provenance status, computes billing totals, and infers jurisdiction.

Key methods:
- ``extract()`` — the single widened LLM call. Returns the raw extracted dict
  (backward-compatible keys plus the per-section provenance payload and a
  ``_master_form`` snapshot).
- ``build_master_form()`` — runs ``extract()`` once and deterministically maps
  the result into a provenance-carrying :class:`MasterClaimForm`. Returns
  ``(form, extracted_dict)``.
- ``finding_from_extraction()`` — derives the OCR ``AgentFinding`` from an
  already-computed extraction (no second LLM call).
- ``analyze()`` — unchanged ``Agent`` contract; only REJECTs on empty/garbled
  text, never on missing structured fields.
"""

from __future__ import annotations

import re
from typing import Any

import sys
from pathlib import Path

_BACKEND_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from utils.normalizers import to_float  # noqa: E402

from ..base import Agent  # noqa: E402
from ..claim_model import (  # noqa: E402
    BillingFlag,
    BillingLine,
    FieldStatus,
    InvestigationItem,
    MedicationItem,
    PolicyStatus,
    ProcedureItem,
    build_empty_master_form,
    field_present,
    infer_jurisdiction,
)
from ..protocol import (  # noqa: E402
    AgentFinding,
    Evidence,
    EvidenceSource,
    JurisdictionProfile,
    MasterClaimForm,
    Verdict,
)


# ---------------------------------------------------------------------------
# Widened extraction schema (design §6.1). Every scalar is reported as
# {value|null, page|null, confidence}. Lists return arrays (possibly empty).
# The LLM is instructed to only report values that literally appear in the
# text — never infer, guess, or carry over from general knowledge.
# ---------------------------------------------------------------------------

_EXTRACTION_SCHEMA = """\
Extract the following fields from the document text. Return strict JSON.

Rules you MUST follow:
- Only report a value that literally appears in the text. If a field is not
  present, return null. Do not infer, guess, or carry over values from
  general knowledge.
- Every scalar field is an object: {"value": <value or null>, "page": <1-based
  page number or null>, "confidence": <0.0-1.0>}.
- List sections are arrays (use [] when nothing is found); each line item's
  fields follow the same {"value","page","confidence"} shape.
- diagnosis_codes / procedure_codes are arrays of short code strings (e.g.
  "J18.9"); strip any trailing description text.

Schema:
{
  "claim_info": {
    "claim_id": {...}, "claim_type": {...}, "submission_date": {...}, "status": {...}
  },
  "patient": {
    "name": {...}, "dob": {...}, "age": {...}, "gender": {...}, "patient_id": {...},
    "address": {...}, "phone": {...}, "email": {...}, "blood_group": {...}, "insurance_id": {...}
  },
  "policy": {
    "insurer_name": {...}, "policy_number": {...}, "policyholder_name": {...},
    "start_date": {...}, "end_date": {...}, "plan_name": {...}, "coverage_type": {...},
    "sum_insured": {...}, "remaining_sum_insured": {...}, "room_rent_limit": {...},
    "copay": {...}, "deductible": {...}, "waiting_period": {...}, "exclusions": {...}
  },
  "provider": {
    "hospital_name": {...}, "address": {...}, "registration_number": {...},
    "provider_id": {...}, "npi": {...}, "doctor_name": {...},
    "doctor_registration_number": {...}, "specialization": {...}, "department": {...}
  },
  "hospitalization": {
    "admission_date": {...}, "admission_time": {...}, "discharge_date": {...},
    "discharge_time": {...}, "admission_type": {...}, "ward": {...}, "bed": {...},
    "icu_stay": {...}, "length_of_stay": {...}
  },
  "clinical": {
    "chief_complaint": {...}, "symptoms": {...}, "findings": {...},
    "primary_diagnosis": {...}, "secondary_diagnoses": {...},
    "diagnosis_codes": {"value": ["code"], "page": null, "confidence": 0.0},
    "history": {...}, "allergies": {...}
  },
  "procedures": [
    {"name": {...}, "code": {...}, "date": {...}, "description": {...}, "doctor": {...}, "amount": {...}}
  ],
  "investigations": [
    {"name": {...}, "date": {...}, "result": {...}, "reference_range": {...}, "amount": {...}}
  ],
  "medications": [
    {"name": {...}, "dosage": {...}, "frequency": {...}, "route": {...}, "start_date": {...}, "end_date": {...}, "amount": {...}}
  ],
  "billing": {
    "line_items": [{"category": {...}, "description": {...}, "amount": {...}}],
    "submitted_total": {...},
    "currency": {...}
  },
  "supporting_documents": {
    "discharge_summary": {"present": true/false, "page": null},
    "hospital_bill": {"present": true/false, "page": null},
    "lab_reports": {"present": true/false, "page": null},
    "imaging_reports": {"present": true/false, "page": null},
    "prescriptions": {"present": true/false, "page": null},
    "medical_records": {"present": true/false, "page": null},
    "policy_document": {"present": true/false, "page": null},
    "identity_document": {"present": true/false, "page": null}
  },
  "confidence": 0.0-1.0,
  "notes": "any extraction caveats"
}
"""

# Policy coverage-term scalars that must NEVER be populated from a non-policy
# source (design §6.1 step 2 — the "never invent coverage" guarantee). Only
# claim-sheet identifiers (policy_number, policyholder_name) may be EXTRACTED.
_POLICY_COVERAGE_TERMS: frozenset[str] = frozenset(
    {
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
    }
)
_POLICY_IDENTITY_SCALARS: frozenset[str] = frozenset(
    {"policy_number", "policyholder_name"}
)

# Section -> scalar attribute names, used by the deterministic mapper.
_SECTION_SCALARS: dict[str, tuple[str, ...]] = {
    "claim_info": ("claim_id", "claim_type", "submission_date", "status"),
    "patient": (
        "name", "dob", "age", "gender", "patient_id", "address", "phone",
        "email", "blood_group", "insurance_id",
    ),
    "provider": (
        "hospital_name", "address", "registration_number", "provider_id",
        "npi", "doctor_name", "doctor_registration_number", "specialization",
        "department",
    ),
    "hospitalization": (
        "admission_date", "admission_time", "discharge_date", "discharge_time",
        "admission_type", "ward", "bed", "icu_stay", "length_of_stay",
    ),
    "clinical": (
        "chief_complaint", "symptoms", "findings", "primary_diagnosis",
        "secondary_diagnoses", "diagnosis_codes", "history", "allergies",
    ),
}

_CODE_FIELDS: frozenset[str] = frozenset({"diagnosis_codes", "procedure_codes"})


class OCRAgent(Agent):
    """Structured field extraction + Master Claim Form population."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the OCR/Extraction Agent in a medical insurance claim processing system. "
            "You receive raw text extracted from a claim document (PDF) and your job is to "
            "identify and extract all structured data fields needed for claim processing. "
            "Be precise about amounts, dates, and medical codes. Only report values that "
            "literally appear in the text; never infer, guess, or fabricate. If a field "
            "cannot be found, report its value as null.\n\n"
            + _EXTRACTION_SCHEMA
        )

    # -- Single widened LLM call ------------------------------------------

    async def extract(self, *, claim_id: str, raw_text: str) -> dict[str, Any]:
        """Single widened extraction call for the Supervisor.

        Returns the parsed LLM payload (per-section provenance envelopes) plus
        backward-compatible flat keys (``patient_name``, ``diagnosis``,
        ``diagnosis_codes``, ``billed_amount``, ``currency``, ``missing_fields``,
        ``confidence``, ``_provider``, ``_model``).
        """
        instructions = (
            f"Extract structured claim fields from the following document text:\n\n"
            f"---BEGIN DOCUMENT---\n{raw_text[:12000]}\n---END DOCUMENT---\n\n"
            f"Apply the extraction schema above. Be thorough but only report "
            f"values literally present in the text."
        )
        # Large schema (~50 fields x 3 keys) — give ample room so the response
        # never truncates into unparsable/empty JSON.
        result = await self.ask_llm_json(instructions, max_tokens=8000)
        parsed: dict[str, Any] = dict(result.parsed or {})

        # --- backward-compatible flat keys ---
        patient = parsed.get("patient") or {}
        clinical = parsed.get("clinical") or {}
        provider = parsed.get("provider") or {}
        billing = parsed.get("billing") or {}

        parsed.setdefault("patient_name", _scalar_value(patient.get("name")))
        parsed.setdefault("provider_name", _scalar_value(provider.get("hospital_name")))
        parsed.setdefault("diagnosis", _scalar_value(clinical.get("primary_diagnosis")))
        parsed.setdefault(
            "diagnosis_codes",
            _normalize_codes(_scalar_value(clinical.get("diagnosis_codes"))),
        )
        parsed.setdefault("billed_amount", _scalar_value(billing.get("submitted_total")))
        parsed.setdefault("currency", _scalar_value(billing.get("currency")))
        parsed.setdefault("confidence", parsed.get("confidence", 0.7))
        parsed.setdefault("notes", parsed.get("notes", ""))

        await self.memory.remember(
            text=(
                f"Extracted claim {claim_id}: diagnosis={parsed.get('diagnosis')}, "
                f"amount={parsed.get('billed_amount')}"
            ),
            metadata={
                "claim_id": claim_id,
                "has_codes": bool(parsed.get("diagnosis_codes")),
            },
        )

        parsed["_provider"] = result.provider
        parsed["_model"] = result.model
        return parsed

    # -- Deterministic Master Claim Form population -----------------------

    async def build_master_form(
        self,
        *,
        claim_id: str,
        raw_text: str,
        source_document: str | None = None,
    ) -> tuple[MasterClaimForm, dict[str, Any]]:
        """Run a single extraction and deterministically build the form.

        Returns ``(form, extracted_dict)`` (design §6.1). The LLM supplies
        values only; code assigns status, computes billing, and infers
        jurisdiction.

        The extraction LLM call occasionally returns a sparse/empty payload
        (truncation or an off response). Since there IS source text, we retry
        up to 3 times until the form actually captures something — so a flaky
        single call never leaves the Master Claim Form blank during a demo.
        """
        has_text = bool((raw_text or "").strip())
        form = None
        extracted: dict[str, Any] = {}
        for _try in range(3):
            extracted = await self.extract(claim_id=claim_id, raw_text=raw_text)

            profile = infer_jurisdiction(raw_text, extracted.get("currency"))
            form = build_empty_master_form(claim_id, profile)

            self._map_sections(form, extracted, source_document)
            self._map_lists(form, extracted, source_document)
            self._map_supporting_documents(form, extracted, source_document)
            self._map_policy(form, extracted, source_document)
            self._compute_billing(form, extracted, source_document)
            self._finalize_claim_info(form, source_document)

            # If the document had text but the form captured nothing, the
            # extraction call likely misfired — retry. Otherwise accept it.
            populated = len(form.all_fields()) - len(form.missing_fields())
            if not has_text or populated > 0:
                break

        extracted["missing_fields"] = form.missing_fields()
        extracted["_master_form"] = form.model_dump(mode="json")
        return form, extracted

    def _map_sections(
        self,
        form: MasterClaimForm,
        extracted: dict[str, Any],
        source_document: str | None,
    ) -> None:
        """Map the plain scalar sections (not policy/billing/docs/lists)."""
        for section_name, attrs in _SECTION_SCALARS.items():
            section = getattr(form, section_name)
            payload = extracted.get(section_name) or {}
            if not isinstance(payload, dict):
                continue
            for attr in attrs:
                cell = payload.get(attr)
                value = _scalar_value(cell)
                if attr in _CODE_FIELDS:
                    value = _normalize_codes(value)
                    if not value:
                        continue
                elif _is_empty(value):
                    continue
                prov = getattr(section, attr)
                _assign(prov, value, cell, source_document)

    def _map_lists(
        self,
        form: MasterClaimForm,
        extracted: dict[str, Any],
        source_document: str | None,
    ) -> None:
        """Map procedures / investigations / medications line items."""
        proc_items = extracted.get("procedures") or []
        if isinstance(proc_items, list) and proc_items:
            items = []
            for raw in proc_items:
                if not isinstance(raw, dict):
                    continue
                items.append(
                    ProcedureItem(
                        name=_line_prov("procedures.name", raw.get("name"), source_document),
                        code=_line_prov("procedures.code", raw.get("code"), source_document),
                        date=_line_prov("procedures.date", raw.get("date"), source_document),
                        description=_line_prov("procedures.description", raw.get("description"), source_document),
                        doctor=_line_prov("procedures.doctor", raw.get("doctor"), source_document),
                        amount=_line_prov("procedures.amount", raw.get("amount"), source_document),
                    )
                )
            if items:
                form.procedures.items = items
                form.procedures.list_status = FieldStatus.EXTRACTED

        inv_items = extracted.get("investigations") or []
        if isinstance(inv_items, list) and inv_items:
            items = []
            for raw in inv_items:
                if not isinstance(raw, dict):
                    continue
                items.append(
                    InvestigationItem(
                        name=_line_prov("investigations.name", raw.get("name"), source_document),
                        date=_line_prov("investigations.date", raw.get("date"), source_document),
                        result=_line_prov("investigations.result", raw.get("result"), source_document),
                        reference_range=_line_prov("investigations.reference_range", raw.get("reference_range"), source_document),
                        amount=_line_prov("investigations.amount", raw.get("amount"), source_document),
                    )
                )
            if items:
                form.investigations.items = items
                form.investigations.list_status = FieldStatus.EXTRACTED

        med_items = extracted.get("medications") or []
        if isinstance(med_items, list) and med_items:
            items = []
            for raw in med_items:
                if not isinstance(raw, dict):
                    continue
                items.append(
                    MedicationItem(
                        name=_line_prov("medications.name", raw.get("name"), source_document),
                        dosage=_line_prov("medications.dosage", raw.get("dosage"), source_document),
                        frequency=_line_prov("medications.frequency", raw.get("frequency"), source_document),
                        route=_line_prov("medications.route", raw.get("route"), source_document),
                        start_date=_line_prov("medications.start_date", raw.get("start_date"), source_document),
                        end_date=_line_prov("medications.end_date", raw.get("end_date"), source_document),
                        amount=_line_prov("medications.amount", raw.get("amount"), source_document),
                    )
                )
            if items:
                form.medications.items = items
                form.medications.list_status = FieldStatus.EXTRACTED

    def _map_supporting_documents(
        self,
        form: MasterClaimForm,
        extracted: dict[str, Any],
        source_document: str | None,
    ) -> None:
        docs = extracted.get("supporting_documents") or {}
        if not isinstance(docs, dict):
            return
        for name in (
            "discharge_summary", "hospital_bill", "lab_reports", "imaging_reports",
            "prescriptions", "medical_records", "policy_document", "identity_document",
        ):
            entry = docs.get(name)
            present = False
            page = None
            if isinstance(entry, dict):
                present = bool(entry.get("present"))
                page = entry.get("page")
            elif isinstance(entry, bool):
                present = entry
            doc = getattr(form.supporting_documents, name)
            if present:
                doc.present = True
                doc.status = FieldStatus.EXTRACTED
                doc.source_document = source_document
                doc.page = page if isinstance(page, int) else None
            # Absent documents stay present=False / status=MISSING (baseline).

    def _map_policy(
        self,
        form: MasterClaimForm,
        extracted: dict[str, Any],
        source_document: str | None,
    ) -> None:
        """Map policy scalars with the coverage-term guard (design §6.1)."""
        payload = extracted.get("policy") or {}
        policy_doc_present = form.supporting_documents.policy_document.present

        if isinstance(payload, dict):
            for attr in _POLICY_IDENTITY_SCALARS:
                cell = payload.get(attr)
                value = _scalar_value(cell)
                if _is_empty(value):
                    continue
                _assign(getattr(form.policy, attr), value, cell, source_document)
            # Coverage-term scalars stay MISSING unless an actual policy
            # document is present (never invent coverage).
            if policy_doc_present:
                for attr in _POLICY_COVERAGE_TERMS:
                    cell = payload.get(attr)
                    value = _scalar_value(cell)
                    if _is_empty(value):
                        continue
                    _assign(getattr(form.policy, attr), value, cell, source_document)

        form.policy.policy_status = (
            PolicyStatus.PRESENT if policy_doc_present else PolicyStatus.MISSING_DOCUMENT
        )

    def _compute_billing(
        self,
        form: MasterClaimForm,
        extracted: dict[str, Any],
        source_document: str | None,
    ) -> None:
        """Billing totals are computed in code, never trusted from the LLM."""
        payload = extracted.get("billing") or {}
        if not isinstance(payload, dict):
            payload = {}

        line_items = payload.get("line_items") or []
        lines: list[BillingLine] = []
        numeric_amounts: list[float] = []
        if isinstance(line_items, list):
            for raw in line_items:
                if not isinstance(raw, dict):
                    continue
                amount_cell = raw.get("amount")
                amount_val = _scalar_value(amount_cell)
                lines.append(
                    BillingLine(
                        category=_line_prov("billing.category", raw.get("category"), source_document),
                        description=_line_prov("billing.description", raw.get("description"), source_document),
                        amount=_line_prov("billing.amount", amount_cell, source_document),
                    )
                )
                num = to_float(amount_val)
                if num is not None:
                    numeric_amounts.append(num)

        form.billing.line_items = lines

        # currency scalar
        currency_cell = payload.get("currency")
        currency_val = _scalar_value(currency_cell)
        if not _is_empty(currency_val):
            _assign(form.billing.currency, currency_val, currency_cell, source_document)

        # submitted total (as stated in the document)
        submitted_cell = payload.get("submitted_total")
        submitted_val = _scalar_value(submitted_cell)
        submitted_num = to_float(submitted_val)
        if submitted_num is not None:
            _assign(form.billing.submitted_total, submitted_num, submitted_cell, source_document)

        calculated = round(sum(numeric_amounts), 2) if numeric_amounts else None
        form.billing.calculated_total = calculated

        if calculated is None or submitted_num is None:
            form.billing.billing_difference = None
            form.billing.flag = BillingFlag.INSUFFICIENT_DATA
            return

        difference = round(submitted_num - calculated, 2)
        form.billing.billing_difference = difference
        if difference == 0:
            form.billing.flag = BillingFlag.BILLING_TOTAL_CONSISTENT
            # Deterministic cross-check passed -> VERIFIED (allowed per §4.1).
            form.billing.submitted_total.status = FieldStatus.VERIFIED
        else:
            form.billing.flag = BillingFlag.BILLING_MISMATCH

    def _finalize_claim_info(
        self, form: MasterClaimForm, source_document: str | None
    ) -> None:
        if source_document:
            form.claim_info.source_documents = [source_document]
        extracted_fields = [
            f for f in form.all_fields()
            if f.status in (FieldStatus.EXTRACTED, FieldStatus.VERIFIED)
        ]
        if extracted_fields:
            mean_conf = sum(f.confidence for f in extracted_fields) / len(extracted_fields)
            form.claim_info.extraction_confidence = round(mean_conf, 4)

    # -- Derived finding (no second LLM call) -----------------------------

    def finding_from_extraction(
        self, *, claim_id: str, extracted: dict[str, Any], raw_text: str = ""
    ) -> AgentFinding:
        """Derive the OCR AgentFinding from an already-computed extraction."""
        missing = extracted.get("missing_fields", []) or []
        conf_value = extracted.get("confidence", 0.7)

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=Verdict.APPROVE,
            confidence=self.make_confidence(
                conf_value, f"Extraction complete; {len(missing)} field(s) missing"
            ),
            reasoning=(
                f"Extracted structured fields into the Master Claim Form; "
                f"{len(missing)} field(s) remain MISSING."
            ),
            evidence=[
                Evidence(
                    source=EvidenceSource.DOCUMENT,
                    field="raw_text",
                    snippet=raw_text[:200],
                )
            ],
            referenced_fields=[k for k in extracted.keys() if not k.startswith("_")],
            tags=["extraction_complete"] if not missing else ["partial_extraction"],
        )

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        raw_text = claim.get("raw_text", "")
        if not raw_text or not str(raw_text).strip():
            return AgentFinding(
                agent=self.role,
                claim_id=claim_id,
                verdict=Verdict.REJECT,
                confidence=self.make_confidence(0.95, "No text provided for extraction"),
                reasoning="Cannot extract fields: no document text was provided.",
                tags=["no_text"],
            )

        _form, extracted = await self.build_master_form(
            claim_id=claim_id,
            raw_text=raw_text,
            source_document=claim.get("source_document"),
        )
        # Missing structured fields are normal and recorded on the form — they
        # never cause a REJECT (design §6.1 step 4).
        return self.finding_from_extraction(
            claim_id=claim_id, extracted=extracted, raw_text=raw_text
        )


# ---------------------------------------------------------------------------
# Module-level helpers (deterministic — no LLM)
# ---------------------------------------------------------------------------


def _scalar_value(cell: Any) -> Any:
    """Pull the ``value`` out of a {value,page,confidence} cell (or a bare value)."""
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def _cell_confidence(cell: Any, default: float = 0.6) -> float:
    if isinstance(cell, dict):
        conf = cell.get("confidence")
        if isinstance(conf, (int, float)):
            return max(0.0, min(1.0, float(conf)))
    return default


def _cell_page(cell: Any) -> int | None:
    if isinstance(cell, dict):
        page = cell.get("page")
        if isinstance(page, int):
            return page
    return None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def _assign(prov: Any, value: Any, cell: Any, source_document: str | None) -> None:
    """Copy an extracted value + provenance into an existing FieldProvenance."""
    confidence = _cell_confidence(cell)
    populated = field_present(
        prov.field,
        value,
        source_document=source_document,
        page=_cell_page(cell),
        confidence=confidence,
    )
    prov.value = populated.value
    prov.source_document = populated.source_document
    prov.page = populated.page
    prov.confidence = populated.confidence
    prov.status = populated.status


def _line_prov(field: str, cell: Any, source_document: str | None) -> Any:
    """Build a FieldProvenance for a line-item cell (present or missing)."""
    from ..claim_model import field_missing

    value = _scalar_value(cell)
    if _is_empty(value):
        return field_missing(field)
    return field_present(
        field,
        value,
        source_document=source_document,
        page=_cell_page(cell),
        confidence=_cell_confidence(cell),
    )


def _normalize_codes(value: Any) -> list[str]:
    """Normalize diagnosis/procedure codes to list[str], stripping descriptions.

    e.g. ``"J18.9 — Pneumonia, unspecified organism"`` -> ``["J18.9"]``.
    """
    if value is None:
        return []
    raw = value if isinstance(value, list) else [value]
    codes: list[str] = []
    for item in raw:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        # Split off trailing description after an em/en dash, hyphen-space, or colon.
        head = re.split(r"\s*[—–:]\s*|\s+-\s+", text, maxsplit=1)[0].strip()
        head = head.strip(" .,;")
        if head:
            codes.append(head)
    return codes


__all__ = ["OCRAgent"]
