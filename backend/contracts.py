from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClaimData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    patient_name: str | None = None
    patient_age: int | None = None
    dob: str | None = None
    gender: str | None = None
    diagnosis: str | None = None
    icd_codes: list[str] | None = None
    procedures: list[str] | None = None
    total_cost: float | None = None
    room_charges: float | None = None
    medicine_charges: float | None = None
    doctor_charges: float | None = None
    admission_date: str | None = None
    discharge_date: str | None = None
    hospital_name: str | None = None
    doctor_name: str | None = None
    policy_number: str | None = None
    pre_auth_number: str | None = None
    tpa_name: str | None = None


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str
    severity: Literal["error", "warning"] = "warning"
    message: str


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    issues: list[ValidationIssue] = Field(default_factory=list)
    rejection_risk: int = 0
    rejection_risk_reason: str = ""
    suggestions: list[str] = Field(default_factory=list)
    is_approvable: bool = False


class CommunicationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email_subject: str = ""
    email_body: str = ""
    whatsapp_message: str = ""


class ProcessResponse(BaseModel):
    claim: ClaimData
    validation: ValidationResult
    form: dict[str, Any]
    comms: CommunicationOutput
