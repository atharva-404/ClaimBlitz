from __future__ import annotations

import json
from typing import Any

from services.llm_client import get_llm_client


NIVA_BUPA_FIELDS = [
    "insured_name",
    "insured_dob",
    "insured_gender",
    "policy_number",
    "pre_authorization_number",
    "hospital_name",
    "hospital_registration_number",
    "treating_doctor",
    "admission_date",
    "discharge_date",
    "diagnosis_primary",
    "icd_code_primary",
    "treatment_type",
    "total_claimed_amount",
    "room_rent_claimed",
    "doctor_fee_claimed",
    "medicine_cost_claimed",
    "patient_signature_required",
    "is_cashless",
]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "null", "none", "n/a", "na", "missing"}
    if isinstance(value, list):
        return len(value) == 0
    return False


def run_form_filler(claim: dict, validation: dict) -> dict:
    prompt = (
        "Map this insurance claim data to NIVA BUPA claim form fields.\n"
        "Return ONLY a JSON object where keys are form field names and values are the filled values.\n"
        "Use null for fields that cannot be determined.\n"
        "Format all dates as DD/MM/YYYY.\n"
        "All money amounts should be numbers (INR).\n\n"
        f"Form fields needed: {NIVA_BUPA_FIELDS}\n\n"
        f"Claim data: {json.dumps(claim, indent=2)}\n"
        f"Validation: {json.dumps(validation, indent=2)}\n\n"
        "Return ONLY the JSON. No explanation."
    )

    raw = get_llm_client().call_json(prompt=prompt, max_tokens=1200)

    form_data = {field: raw.get(field) for field in NIVA_BUPA_FIELDS}

    for field, value in form_data.items():
        if isinstance(value, str) and value.strip().lower() in {"", "null", "none", "n/a", "na", "missing"}:
            form_data[field] = None

    filled_count = sum(1 for field in NIVA_BUPA_FIELDS if not _is_missing(form_data.get(field)))

    form_data["_filled_count"] = filled_count
    form_data["_total_fields"] = len(NIVA_BUPA_FIELDS)
    form_data["_validation_issues"] = validation.get("issues", [])

    return form_data
