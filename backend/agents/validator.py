from __future__ import annotations

import json

from contracts import ValidationResult
from services.llm_client import get_llm_client
from utils.normalizers import to_int, to_str, to_str_list


def run_validator(claim: dict) -> dict:
    prompt = (
        "You are an expert Indian insurance claim validator working for a TPA.\n"
        "Analyze this insurance claim data and return ONLY a valid JSON object with no explanation.\n\n"
        "Check for:\n"
        "1. Missing mandatory fields (policy_number, pre_auth_number, icd_codes, total_cost, admission_date, discharge_date)\n"
        "2. Invalid or suspicious ICD-10 codes (codes that don't exist or don't match the diagnosis)\n"
        "3. Cost anomalies (e.g., total_cost doesn't add up to room + medicine + doctor charges)\n"
        "4. Missing doctor name or hospital name\n"
        "5. Date issues (discharge before admission, future dates)\n\n"
        "Return this exact JSON structure:\n"
        "{\n"
        "  \"issues\": [\n"
        "    {\"field\": \"field_name\", \"severity\": \"error|warning\", \"message\": \"what is wrong\"}\n"
        "  ],\n"
        "  \"rejection_risk\": <integer 0-100>,\n"
        "  \"rejection_risk_reason\": \"one sentence explaining the main risk\",\n"
        "  \"suggestions\": [\"actionable fix 1\", \"actionable fix 2\"],\n"
        "  \"is_approvable\": <true|false>\n"
        "}\n\n"
        "rejection_risk guide: 0-20 = very likely approved, 21-50 = minor issues, 51-80 = likely rejected, 81-100 = will be rejected.\n\n"
        f"CLAIM DATA:\n{json.dumps(claim, indent=2)}"
    )

    raw = get_llm_client().call_json(prompt=prompt, max_tokens=1200)

    issues = []
    for issue in raw.get("issues", []):
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity", "warning")).lower()
        if severity not in {"error", "warning"}:
            severity = "warning"
        issues.append(
            {
                "field": to_str(issue.get("field")) or "unknown",
                "severity": severity,
                "message": to_str(issue.get("message")) or "Issue detected",
            }
        )

    risk = to_int(raw.get("rejection_risk")) or 0
    risk = max(0, min(100, risk))

    validation = ValidationResult(
        issues=issues,
        rejection_risk=risk,
        rejection_risk_reason=to_str(raw.get("rejection_risk_reason")) or "No risk reason provided",
        suggestions=to_str_list(raw.get("suggestions")) or [],
        is_approvable=bool(raw.get("is_approvable", False)),
    )

    return validation.model_dump()
