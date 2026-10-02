"""The canonical, provenance-carrying Master Claim Form and its support types.

This module is the content agents reason over (what a claim *is*), kept
separate from ``protocol.py`` (the envelope agents speak in). It is pure data
plus a few deterministic helpers:

- a provenance envelope (``FieldProvenance``) so every scalar carries where it
  came from and whether it is EXTRACTED / MISSING / CONFLICT / VERIFIED /
  LOW_CONFIDENCE — no field is ever fabricated;
- the twelve-section ``MasterClaimForm`` and its line-item models;
- jurisdiction inference (``infer_jurisdiction``) driven deterministically by
  currency/₹/+91/$-ZIP, never by the LLM;
- a decomposed ``RiskBreakdown`` (documentation/policy/clinical/billing/fraud/
  overall) with ``blocking_conditions`` the Judge consumes;
- factories (``build_empty_master_form``, ``field_present`` /
  ``field_missing`` / ``field_conflict``) and ``AGENT_DISPLAY_NAMES``.

Import-cycle guard (design §3): this module must NOT import
``AgentFinding``/``AgentMessage`` from ``protocol``. The two confidence
thresholds are redefined here as literals, and ``now_utc``/``new_id`` are
imported lazily inside functions. The only import-time edge is
``protocol`` → ``claim_model`` (via protocol's re-export block).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# NOTE: this module deliberately does NOT import from .protocol at module
# load time. protocol.py re-exports claim_model at its own bottom, so a
# top-level `from .protocol import ...` here would create a circular import
# whenever claim_model is imported first. AgentRole / now_utc are resolved
# lazily inside functions (see AGENT_DISPLAY_NAMES below and
# build_empty_master_form). See design §3.

# ---------------------------------------------------------------------------
# Confidence thresholds (redefined locally as literals to avoid an import-time
# dependency on protocol.py — see design §3 / §4.1). These mirror
# HUMAN_ESCALATION_CONFIDENCE_THRESHOLD / LOW_CONFIDENCE_THRESHOLD in protocol.
# ---------------------------------------------------------------------------

HIGH_CONFIDENCE_THRESHOLD = 0.80
LOW_CONFIDENCE_THRESHOLD = 0.50

# Band thresholds for _band_from_score (design §8.5): lowMax 0.3, mediumMax 0.6.
_BAND_LOW_MAX = 0.3
_BAND_MEDIUM_MAX = 0.6


def _band_from_score(score: float) -> str:
    """Map a 0.0-1.0 risk score to one of ``low`` | ``medium`` | ``high``.

    Only ever yields three bands (design §8.5): a ``critical`` fourth label is
    collapsed into ``high`` by construction, since this is the sole band source.
    """
    if score <= _BAND_LOW_MAX:
        return "low"
    if score <= _BAND_MEDIUM_MAX:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# Provenance envelope — the atomic unit (design §4.1)
# ---------------------------------------------------------------------------


class FieldStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"
    VERIFIED = "VERIFIED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class ConflictingValue(BaseModel):
    """One observed value for a field, preserved when a CONFLICT is recorded."""

    model_config = ConfigDict(extra="ignore")

    value: Any = None
    source_document: str | None = None
    page: int | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class FieldProvenance(BaseModel):
    """A scalar value plus where it came from and how much we trust it.

    Every scalar field in the Master Claim Form is one of these, never a bare
    value, so each cell is independently traceable and auditable.
    """

    model_config = ConfigDict(extra="ignore")

    field: str                              # dotted path, e.g. "patient.name"
    value: Any | None = None                # null when MISSING
    source_document: str | None = None      # filename/doc id the value came from
    page: int | None = None                 # 1-based page number, null if unknown
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    status: FieldStatus = FieldStatus.MISSING
    conflicts: list[ConflictingValue] = Field(default_factory=list)
    note: str | None = None                 # optional extraction caveat


# ---------------------------------------------------------------------------
# Status enums owned by the model (design §4.3)
# ---------------------------------------------------------------------------


class PolicyStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CoverageStatus(str, Enum):
    COVERED = "COVERED"
    NOT_COVERED = "NOT_COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class BillingFlag(str, Enum):
    BILLING_TOTAL_CONSISTENT = "BILLING_TOTAL_CONSISTENT"   # difference == 0
    BILLING_MISMATCH = "BILLING_MISMATCH"                   # difference != 0
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"                 # no items / no total


# ---------------------------------------------------------------------------
# Section models (design §4.2). Scalars are FieldProvenance; lists carry a
# list_status: FieldStatus (MISSING when no items were found).
# ---------------------------------------------------------------------------


class ClaimInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim_id: FieldProvenance
    claim_type: FieldProvenance            # e.g. "inpatient hospitalization"
    submission_date: FieldProvenance
    status: FieldProvenance                # requested claim status
    source_documents: list[str] = Field(default_factory=list)
    extraction_confidence: float = 0.0     # mean confidence across EXTRACTED fields


class Patient(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: FieldProvenance
    dob: FieldProvenance
    age: FieldProvenance
    gender: FieldProvenance
    patient_id: FieldProvenance
    address: FieldProvenance
    phone: FieldProvenance
    email: FieldProvenance
    blood_group: FieldProvenance
    insurance_id: FieldProvenance


class Policy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    insurer_name: FieldProvenance
    policy_number: FieldProvenance
    policyholder_name: FieldProvenance
    start_date: FieldProvenance
    end_date: FieldProvenance
    plan_name: FieldProvenance
    coverage_type: FieldProvenance
    sum_insured: FieldProvenance
    remaining_sum_insured: FieldProvenance
    room_rent_limit: FieldProvenance
    copay: FieldProvenance
    deductible: FieldProvenance
    waiting_period: FieldProvenance
    exclusions: FieldProvenance
    policy_status: PolicyStatus = PolicyStatus.MISSING_DOCUMENT


class Provider(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hospital_name: FieldProvenance
    address: FieldProvenance
    registration_number: FieldProvenance
    provider_id: FieldProvenance
    npi: FieldProvenance                   # NOT mandatory outside US (jurisdiction-aware)
    doctor_name: FieldProvenance
    doctor_registration_number: FieldProvenance
    specialization: FieldProvenance
    department: FieldProvenance


class Hospitalization(BaseModel):
    model_config = ConfigDict(extra="ignore")

    admission_date: FieldProvenance
    admission_time: FieldProvenance
    discharge_date: FieldProvenance
    discharge_time: FieldProvenance
    admission_type: FieldProvenance
    ward: FieldProvenance
    bed: FieldProvenance
    icu_stay: FieldProvenance
    length_of_stay: FieldProvenance


class Clinical(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chief_complaint: FieldProvenance
    symptoms: FieldProvenance
    findings: FieldProvenance
    primary_diagnosis: FieldProvenance
    secondary_diagnoses: FieldProvenance
    diagnosis_codes: FieldProvenance       # value is list[str] when present
    history: FieldProvenance
    allergies: FieldProvenance


class ProcedureItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: FieldProvenance
    code: FieldProvenance
    date: FieldProvenance
    description: FieldProvenance
    doctor: FieldProvenance
    amount: FieldProvenance


class Procedures(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[ProcedureItem] = Field(default_factory=list)
    list_status: FieldStatus = FieldStatus.MISSING


class InvestigationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: FieldProvenance
    date: FieldProvenance
    result: FieldProvenance
    reference_range: FieldProvenance
    amount: FieldProvenance


class Investigations(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[InvestigationItem] = Field(default_factory=list)
    list_status: FieldStatus = FieldStatus.MISSING


class MedicationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: FieldProvenance
    dosage: FieldProvenance
    frequency: FieldProvenance
    route: FieldProvenance
    start_date: FieldProvenance
    end_date: FieldProvenance
    amount: FieldProvenance


class Medications(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[MedicationItem] = Field(default_factory=list)
    list_status: FieldStatus = FieldStatus.MISSING


class BillingLine(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: FieldProvenance
    description: FieldProvenance
    amount: FieldProvenance


class Billing(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line_items: list[BillingLine] = Field(default_factory=list)
    calculated_total: float | None = None     # computed in code, NOT from the LLM
    submitted_total: FieldProvenance          # as stated in the document
    billing_difference: float | None = None   # submitted - calculated
    flag: BillingFlag = BillingFlag.INSUFFICIENT_DATA
    currency: FieldProvenance


class DocPresence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    present: bool = False
    source_document: str | None = None
    page: int | None = None
    status: FieldStatus = FieldStatus.MISSING   # EXTRACTED when a line asserts presence


class SupportingDocuments(BaseModel):
    model_config = ConfigDict(extra="ignore")

    discharge_summary: DocPresence
    hospital_bill: DocPresence
    lab_reports: DocPresence
    imaging_reports: DocPresence
    prescriptions: DocPresence
    medical_records: DocPresence
    policy_document: DocPresence
    identity_document: DocPresence
    other: list[DocPresence] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Jurisdiction / claim-standard config (design §5)
# ---------------------------------------------------------------------------


class Jurisdiction(str, Enum):
    IN = "IN"
    US = "US"
    OTHER = "OTHER"


# Backwards/forwards-friendly alias: the design's re-export list names
# ``ClaimStandard`` alongside the jurisdiction types. It is the same concept.
ClaimStandard = Jurisdiction


class JurisdictionProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jurisdiction: Jurisdiction = Jurisdiction.IN
    currency: str | None = None                 # e.g. "INR", "USD"
    npi_required: bool = False                  # US True, IN/OTHER False
    procedure_coding_required: bool = False     # CPT/HCPCS required? US True, IN False
    provider_registration_expected: bool = True # expected but not fatal in IN
    inferred_from: str = "default"              # "currency:INR", "content", "explicit"


# Requirement-flag table per jurisdiction (design §5).
_JURISDICTION_FLAGS: dict[Jurisdiction, dict[str, bool]] = {
    Jurisdiction.IN: {
        "npi_required": False,
        "procedure_coding_required": False,
        "provider_registration_expected": True,
    },
    Jurisdiction.US: {
        "npi_required": True,
        "procedure_coding_required": True,
        "provider_registration_expected": True,
    },
    Jurisdiction.OTHER: {
        "npi_required": False,
        "procedure_coding_required": False,
        "provider_registration_expected": True,
    },
}


def infer_jurisdiction(
    raw_text: str | None,
    extracted_currency: str | None = None,
) -> JurisdictionProfile:
    """Deterministically infer the jurisdiction profile (design §5).

    Rules (never the LLM):
      1. INR currency, or ``₹`` / ``INR`` / a ``+91`` phone prefix in text → IN.
      2. USD / ``$`` combined with a US-style ZIP or ``NPI`` token → US.
      3. Otherwise → OTHER with conservative defaults.
    Requirement flags come from the profile table above.
    """
    text = raw_text or ""
    text_upper = text.upper()
    currency = (extracted_currency or "").strip().upper()

    jurisdiction = Jurisdiction.OTHER
    inferred_from = "default"

    in_signal = (
        currency == "INR"
        or "₹" in text
        or "INR" in text_upper
        or "+91" in text
    )
    us_signal = currency == "USD" or "$" in text

    if in_signal:
        jurisdiction = Jurisdiction.IN
        if currency == "INR":
            inferred_from = "currency:INR"
        else:
            inferred_from = "content"
    elif us_signal and ("NPI" in text_upper or _has_us_zip(text)):
        jurisdiction = Jurisdiction.US
        inferred_from = "currency:USD" if currency == "USD" else "content"

    flags = _JURISDICTION_FLAGS[jurisdiction]
    return JurisdictionProfile(
        jurisdiction=jurisdiction,
        currency=(extracted_currency or None),
        npi_required=flags["npi_required"],
        procedure_coding_required=flags["procedure_coding_required"],
        provider_registration_expected=flags["provider_registration_expected"],
        inferred_from=inferred_from,
    )


def _has_us_zip(text: str) -> bool:
    """True if the text contains a plausible US ZIP (5 digits or ZIP+4)."""
    import re

    return re.search(r"\b\d{5}(?:-\d{4})?\b", text) is not None


# ---------------------------------------------------------------------------
# Top-level Master Claim Form (design §4.4)
# ---------------------------------------------------------------------------


class MasterClaimForm(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim_id: str
    jurisdiction: JurisdictionProfile
    claim_info: ClaimInfo
    patient: Patient
    policy: Policy
    provider: Provider
    hospitalization: Hospitalization
    clinical: Clinical
    procedures: Procedures
    investigations: Investigations
    medications: Medications
    billing: Billing
    supporting_documents: SupportingDocuments
    generated_at: datetime
    schema_version: str = "1.0"

    def all_fields(self) -> list[FieldProvenance]:
        """Flat list of every scalar FieldProvenance, for status rollups / UI."""
        fields: list[FieldProvenance] = []

        def collect(model: BaseModel) -> None:
            for value in model.__dict__.values():
                if isinstance(value, FieldProvenance):
                    fields.append(value)
                elif isinstance(value, BaseModel):
                    collect(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, FieldProvenance):
                            fields.append(item)
                        elif isinstance(item, BaseModel):
                            collect(item)

        for section in (
            self.claim_info,
            self.patient,
            self.policy,
            self.provider,
            self.hospitalization,
            self.clinical,
            self.procedures,
            self.investigations,
            self.medications,
            self.billing,
            self.supporting_documents,
        ):
            collect(section)
        return fields

    def missing_fields(self) -> list[str]:
        """Dotted paths of every field currently marked MISSING."""
        return [f.field for f in self.all_fields() if f.status == FieldStatus.MISSING]

    def conflict_fields(self) -> list[str]:
        """Dotted paths of every field currently marked CONFLICT."""
        return [f.field for f in self.all_fields() if f.status == FieldStatus.CONFLICT]


# ---------------------------------------------------------------------------
# Decomposed risk engine (design §8.5)
# ---------------------------------------------------------------------------


class RiskDimension(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str                       # documentation|policy|clinical|billing|fraud|overall_review
    score: float = Field(ge=0.0, le=1.0)
    band: str                       # low|medium|high (derived)
    drivers: list[str] = Field(default_factory=list)   # evidence-cited reasons
    blocking: bool = False          # a condition that forces REVIEW regardless of score


class RiskBreakdown(BaseModel):
    model_config = ConfigDict(extra="ignore")

    documentation_risk: RiskDimension
    policy_risk: RiskDimension
    clinical_risk: RiskDimension
    billing_risk: RiskDimension
    fraud_risk: RiskDimension
    overall_review_risk: RiskDimension
    blocking_conditions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent display names (design §8.2). The AgentRole enum values are kept for
# wire/DB compatibility; UI/prompts render these human-facing labels.
#
# Built lazily via module __getattr__ so this module has no import-time
# dependency on protocol.AgentRole (which would be circular — see §3). The
# dict is keyed by AgentRole and cached on first access.
# ---------------------------------------------------------------------------

# Human-facing labels keyed by AgentRole.value (plain strings, no import).
_AGENT_DISPLAY_NAMES_BY_VALUE: dict[str, str] = {
    "supervisor": "Supervisor Agent",
    "scanner": "Document Scanner Agent",
    "ocr": "OCR/Extraction Agent",
    "validator": "Validator Agent",
    "medical_expert": "Clinical Consistency Agent",
    "policy_expert": "Policy Expert Agent",
    "fraud_detection": "Fraud Detection Agent",
    "risk_assessment": "Risk Assessment Agent",
    "communication": "Communication Agent",
    "judge": "Judge Agent",
}

_AGENT_DISPLAY_NAMES_CACHE: dict[Any, str] | None = None


def _build_agent_display_names() -> dict[Any, str]:
    """Build the AgentRole-keyed display-name map, importing AgentRole lazily."""
    from .protocol import AgentRole

    return {role: _AGENT_DISPLAY_NAMES_BY_VALUE[role.value] for role in AgentRole}


def __getattr__(name: str) -> Any:
    """Lazily expose AGENT_DISPLAY_NAMES to avoid an import-time cycle (§3)."""
    if name == "AGENT_DISPLAY_NAMES":
        global _AGENT_DISPLAY_NAMES_CACHE
        if _AGENT_DISPLAY_NAMES_CACHE is None:
            _AGENT_DISPLAY_NAMES_CACHE = _build_agent_display_names()
        return _AGENT_DISPLAY_NAMES_CACHE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Factories (design §4.1 / §4.4)
# ---------------------------------------------------------------------------


def field_missing(field: str) -> FieldProvenance:
    """A MISSING field: value None, no source/page, confidence 0.0."""
    return FieldProvenance(
        field=field,
        value=None,
        source_document=None,
        page=None,
        confidence=0.0,
        status=FieldStatus.MISSING,
    )


def field_present(
    field: str,
    value: Any,
    *,
    source_document: str | None = None,
    page: int | None = None,
    confidence: float = 0.0,
    note: str | None = None,
) -> FieldProvenance:
    """A present field.

    Status is derived from confidence (design §4.1): below
    ``LOW_CONFIDENCE_THRESHOLD`` (0.50) → LOW_CONFIDENCE, otherwise EXTRACTED.
    """
    status = (
        FieldStatus.EXTRACTED
        if confidence >= LOW_CONFIDENCE_THRESHOLD
        else FieldStatus.LOW_CONFIDENCE
    )
    return FieldProvenance(
        field=field,
        value=value,
        source_document=source_document,
        page=page,
        confidence=confidence,
        status=status,
        note=note,
    )


def field_conflict(field: str, options: list[ConflictingValue]) -> FieldProvenance:
    """A CONFLICT field.

    The primary value is the first observed option; every observed option
    (including the primary) is preserved in ``conflicts`` so nothing is
    discarded (design §4.1).
    """
    primary = options[0] if options else ConflictingValue()
    return FieldProvenance(
        field=field,
        value=primary.value,
        source_document=primary.source_document,
        page=primary.page,
        confidence=primary.confidence,
        status=FieldStatus.CONFLICT,
        conflicts=list(options),
    )


def _empty_claim_info(claim_id: str) -> ClaimInfo:
    return ClaimInfo(
        claim_id=field_missing("claim_info.claim_id"),
        claim_type=field_missing("claim_info.claim_type"),
        submission_date=field_missing("claim_info.submission_date"),
        status=field_missing("claim_info.status"),
        source_documents=[],
        extraction_confidence=0.0,
    )


def _empty_patient() -> Patient:
    p = "patient."
    return Patient(
        name=field_missing(p + "name"),
        dob=field_missing(p + "dob"),
        age=field_missing(p + "age"),
        gender=field_missing(p + "gender"),
        patient_id=field_missing(p + "patient_id"),
        address=field_missing(p + "address"),
        phone=field_missing(p + "phone"),
        email=field_missing(p + "email"),
        blood_group=field_missing(p + "blood_group"),
        insurance_id=field_missing(p + "insurance_id"),
    )


def _empty_policy() -> Policy:
    p = "policy."
    return Policy(
        insurer_name=field_missing(p + "insurer_name"),
        policy_number=field_missing(p + "policy_number"),
        policyholder_name=field_missing(p + "policyholder_name"),
        start_date=field_missing(p + "start_date"),
        end_date=field_missing(p + "end_date"),
        plan_name=field_missing(p + "plan_name"),
        coverage_type=field_missing(p + "coverage_type"),
        sum_insured=field_missing(p + "sum_insured"),
        remaining_sum_insured=field_missing(p + "remaining_sum_insured"),
        room_rent_limit=field_missing(p + "room_rent_limit"),
        copay=field_missing(p + "copay"),
        deductible=field_missing(p + "deductible"),
        waiting_period=field_missing(p + "waiting_period"),
        exclusions=field_missing(p + "exclusions"),
        policy_status=PolicyStatus.MISSING_DOCUMENT,
    )


def _empty_provider() -> Provider:
    p = "provider."
    return Provider(
        hospital_name=field_missing(p + "hospital_name"),
        address=field_missing(p + "address"),
        registration_number=field_missing(p + "registration_number"),
        provider_id=field_missing(p + "provider_id"),
        npi=field_missing(p + "npi"),
        doctor_name=field_missing(p + "doctor_name"),
        doctor_registration_number=field_missing(p + "doctor_registration_number"),
        specialization=field_missing(p + "specialization"),
        department=field_missing(p + "department"),
    )


def _empty_hospitalization() -> Hospitalization:
    p = "hospitalization."
    return Hospitalization(
        admission_date=field_missing(p + "admission_date"),
        admission_time=field_missing(p + "admission_time"),
        discharge_date=field_missing(p + "discharge_date"),
        discharge_time=field_missing(p + "discharge_time"),
        admission_type=field_missing(p + "admission_type"),
        ward=field_missing(p + "ward"),
        bed=field_missing(p + "bed"),
        icu_stay=field_missing(p + "icu_stay"),
        length_of_stay=field_missing(p + "length_of_stay"),
    )


def _empty_clinical() -> Clinical:
    p = "clinical."
    return Clinical(
        chief_complaint=field_missing(p + "chief_complaint"),
        symptoms=field_missing(p + "symptoms"),
        findings=field_missing(p + "findings"),
        primary_diagnosis=field_missing(p + "primary_diagnosis"),
        secondary_diagnoses=field_missing(p + "secondary_diagnoses"),
        diagnosis_codes=field_missing(p + "diagnosis_codes"),
        history=field_missing(p + "history"),
        allergies=field_missing(p + "allergies"),
    )


def _empty_billing() -> Billing:
    p = "billing."
    return Billing(
        line_items=[],
        calculated_total=None,
        submitted_total=field_missing(p + "submitted_total"),
        billing_difference=None,
        flag=BillingFlag.INSUFFICIENT_DATA,
        currency=field_missing(p + "currency"),
    )


def _empty_doc(name: str) -> DocPresence:
    return DocPresence(name=name, present=False, status=FieldStatus.MISSING)


def _empty_supporting_documents() -> SupportingDocuments:
    return SupportingDocuments(
        discharge_summary=_empty_doc("discharge_summary"),
        hospital_bill=_empty_doc("hospital_bill"),
        lab_reports=_empty_doc("lab_reports"),
        imaging_reports=_empty_doc("imaging_reports"),
        prescriptions=_empty_doc("prescriptions"),
        medical_records=_empty_doc("medical_records"),
        policy_document=_empty_doc("policy_document"),
        identity_document=_empty_doc("identity_document"),
        other=[],
    )


def build_empty_master_form(
    claim_id: str,
    jurisdiction: JurisdictionProfile,
) -> MasterClaimForm:
    """The authoritative "nothing fabricated" baseline (design §4.4).

    Every scalar FieldProvenance has ``status == MISSING`` and every list has
    ``list_status == MISSING``. The OCR agent fills this in from what the
    documents actually contain.
    """
    # Imported lazily to keep claim_model import-time independent of protocol.
    from .protocol import now_utc

    return MasterClaimForm(
        claim_id=claim_id,
        jurisdiction=jurisdiction,
        claim_info=_empty_claim_info(claim_id),
        patient=_empty_patient(),
        policy=_empty_policy(),
        provider=_empty_provider(),
        hospitalization=_empty_hospitalization(),
        clinical=_empty_clinical(),
        procedures=Procedures(items=[], list_status=FieldStatus.MISSING),
        investigations=Investigations(items=[], list_status=FieldStatus.MISSING),
        medications=Medications(items=[], list_status=FieldStatus.MISSING),
        billing=_empty_billing(),
        supporting_documents=_empty_supporting_documents(),
        generated_at=now_utc(),
        schema_version="1.0",
    )


__all__ = [
    # thresholds / helpers
    "HIGH_CONFIDENCE_THRESHOLD",
    "LOW_CONFIDENCE_THRESHOLD",
    "_band_from_score",
    # provenance envelope
    "FieldStatus",
    "ConflictingValue",
    "FieldProvenance",
    # status enums
    "PolicyStatus",
    "CoverageStatus",
    "BillingFlag",
    # section models
    "ClaimInfo",
    "Patient",
    "Policy",
    "Provider",
    "Hospitalization",
    "Clinical",
    "ProcedureItem",
    "Procedures",
    "InvestigationItem",
    "Investigations",
    "MedicationItem",
    "Medications",
    "BillingLine",
    "Billing",
    "DocPresence",
    "SupportingDocuments",
    # jurisdiction
    "Jurisdiction",
    "ClaimStandard",
    "JurisdictionProfile",
    "infer_jurisdiction",
    # top-level form
    "MasterClaimForm",
    # risk
    "RiskDimension",
    "RiskBreakdown",
    # display names
    "AGENT_DISPLAY_NAMES",
    # factories
    "field_missing",
    "field_present",
    "field_conflict",
    "build_empty_master_form",
]
