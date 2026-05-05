import json
import os
import re
from datetime import date, datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import httpx

from pypdf import PdfReader

from app.models import ClaimData, ProcessResponse, RiskContribution, RiskModelInfo

ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}
ICD10_PATTERN = re.compile(r"[A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?", re.IGNORECASE)
CPT_PATTERN = re.compile(r"\b\d{5}\b")
IN_NETWORK_PROVIDERS = {
    "SUMMIT HEALTH CLINIC",
    "CITY CARE HOSPITAL",
    "LIFELINE MEDICAL CENTER",
}


class UnsupportedFileError(ValueError):
    pass


class ExtractionError(ValueError):
    pass


def _configure_tesseract() -> None:
    try:
        import pytesseract
    except ImportError:
        return

    common_paths = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]
    for exe_path in common_paths:
        if exe_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(exe_path)
            return


def _normalize_file_type(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise UnsupportedFileError(
            "Unsupported file type. Please upload PDF, PNG, JPG, or JPEG."
        )


def _extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    if text:
        return text

    # Fallback for scanned/image-only PDFs where embedded text is unavailable.
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
    except ImportError:
        # Continue with empty text so the pipeline can still return a structured
        # best-effort response with fallback defaults.
        return ""

    try:
        ocr_pages: list[str] = []
        _configure_tesseract()
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_pages.append(pytesseract.image_to_string(image) or "")
    except pytesseract.TesseractNotFoundError:
        # OCR runtime missing; do not fail hard.
        return ""

    ocr_text = "\n".join(ocr_pages).strip()
    if not ocr_text:
        return ""

    return ocr_text


def _extract_image_text(file_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    try:
        _configure_tesseract()
        image = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(image).strip()
    except pytesseract.TesseractNotFoundError:
        return ""

    if not text:
        return ""
    return text


def _extract_text(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf_text(file_bytes)

    return _extract_image_text(file_bytes)


def _find_first_group(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _parse_currency(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _find_amount(text: str, labels: list[str]) -> float | None:
    for label in labels:
        pattern = rf"{label}\s*[:=-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]{{2}})?)"
        value = _find_first_group(text, [pattern])
        amount = _parse_currency(value)
        if amount is not None:
            return amount
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None

    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _extract_claim_data(text: str) -> tuple[ClaimData, list[str]]:
    issues: list[str] = []

    patient_name = _find_first_group(text, [
        r"patient(?:'s)?\s+name\s*[:=-]\s*([A-Za-z .,'-]{3,})",
        r"patient(?:'s)?\s+name\s+([A-Za-z .,'-]{3,})",
        r"name\s*[:=-]\s*([A-Za-z .,'-]{3,})",
    ]) or "Unknown Patient"

    policy_number = _find_first_group(text, [
        r"policy(?:\s*(?:number|no\.?|#))?\s*[:#=-]?\s*([A-Z0-9-]{6,})",
        r"insured(?:'s)?\s+id\s*[:#=-]?\s*([A-Z0-9-]{6,})",
    ])
    if not policy_number:
        issues.append("Missing policy number")
        policy_number = "UNKNOWN-POLICY"

    dob_raw = _find_first_group(text, [
        r"(?:dob|date\s+of\s+birth)\s*[:=-]\s*([0-9./-]{8,10})",
        r"(?:dob|date\s+of\s+birth)\s+([0-9./-]{8,10})",
    ])
    dob = _parse_date(dob_raw)
    if not dob:
        issues.append("Missing or invalid date of birth")
        dob = date(1970, 1, 1)

    dos_raw = _find_first_group(text, [
        r"(?:date\s+of\s+service|service\s+date)\s*[:=-]\s*([0-9./-]{8,10})",
        r"(?:date\s+of\s+service|service\s+date)\s+([0-9./-]{8,10})",
    ])
    date_of_service = _parse_date(dos_raw)
    if not date_of_service:
        issues.append("Missing or invalid date of service")
        date_of_service = date.today()

    diagnosis_code_match = ICD10_PATTERN.search(text)
    diagnosis_code = diagnosis_code_match.group(0).upper() if diagnosis_code_match else "UNKNOWN"
    if diagnosis_code == "UNKNOWN":
        issues.append("Missing ICD-10 diagnosis code")

    diagnosis_desc = _find_first_group(text, [
        r"diagnosis(?:\s+description)?\s*[:=-]\s*([A-Za-z0-9 ,()'/-]{4,})",
        r"diagnosis(?:\s+description)?\s+([A-Za-z0-9 ,()'/-]{4,})",
    ]) or "Description unavailable"

    cpt_match = re.search(r"(?:cpt|procedure\s+code)\s*[:=-]?\s*(\d{5})", text, re.IGNORECASE)
    if cpt_match:
        cpt_code = cpt_match.group(1)
    else:
        any_cpt = CPT_PATTERN.search(text)
        cpt_code = any_cpt.group(0) if any_cpt else "00000"
        if cpt_code == "00000":
            issues.append("Missing CPT procedure code")

    provider = _find_first_group(text, [
        r"(?:provider|hospital|clinic)\s*[:=-]\s*([A-Za-z0-9 .,&'-]{4,})",
        r"billing\s+provider\s*[:=-]\s*([A-Za-z0-9 .,&'-]{4,})",
        r"billing\s+provider\s+([A-Za-z0-9 .,&'-]{4,})",
    ]) or "Unknown Provider"

    total_billed = _find_amount(text, [
        r"total\s+billed",
        r"total\s+charge",
        r"claim\s+amount",
        r"charges",
    ])
    if total_billed is None:
        issues.append("Missing total billed amount")
        total_billed = 0.0

    approved_amount = _find_amount(text, [
        r"approved\s+amount",
        r"allowed\s+amount",
        r"payable\s+amount",
    ])
    if approved_amount is None:
        approved_amount = round(total_billed * 0.7, 2)
        issues.append("Approved amount not found; estimated as 70% of billed amount")

    patient_responsibility = _find_amount(text, [
        r"patient\s+responsibility",
        r"patient\s+share",
        r"co-?pay",
        r"coinsurance",
        r"your\s+cost",
    ])
    if patient_responsibility is None:
        patient_responsibility = max(total_billed - approved_amount, 0)
        issues.append("Patient responsibility not found; derived from billed - approved")

    claim = ClaimData(
        patientName=patient_name,
        dob=dob,
        policyNumber=policy_number,
        diagnosisCode=diagnosis_code,
        diagnosisDesc=diagnosis_desc,
        cptCode=cpt_code,
        provider=provider,
        totalBilled=total_billed,
        approvedAmount=approved_amount,
        patientResponsibility=patient_responsibility,
        dateOfService=date_of_service,
    )

    return claim, issues


def _risk_band(score: float) -> tuple[str, str]:
    if score <= 0.30:
        return "LOW", "APPROVE"
    if score <= 0.60:
        return "MEDIUM", "REVIEW"
    return "HIGH", "REJECT"


def _calculate_risk_rules(
    claim: ClaimData,
    issues: list[str],
) -> tuple[float, str, str, list[str], list[RiskContribution], RiskModelInfo]:
    base_score = 0.10
    score = base_score
    reasons: list[str] = []
    contributions: list[RiskContribution] = []

    def apply_rule(rule: str, delta: float, reason: str) -> None:
        nonlocal score
        score += delta
        reasons.append(reason)
        contributions.append(RiskContribution(rule=rule, delta=round(delta, 2), reason=reason))

    ratio = claim.approvedAmount / claim.totalBilled if claim.totalBilled > 0 else 0

    if claim.totalBilled <= 0:
        apply_rule("invalid_total_billed", 0.45, "Total billed amount is invalid")

    if ratio < 0.4:
        apply_rule("low_approval_ratio", 0.35, "Low approval ratio compared with billed amount")
    elif ratio < 0.6:
        apply_rule("moderate_approval_ratio", 0.22, "Moderate approval ratio; manual review recommended")
    elif ratio < 0.8:
        apply_rule("slight_approval_variance", 0.10, "Slight variance between approved and billed amount")

    if claim.totalBilled > 100000:
        apply_rule("very_high_claim_amount", 0.20, "High claim amount above threshold")
    elif claim.totalBilled > 50000:
        apply_rule("high_claim_amount", 0.12, "Claim amount is above normal operating range")

    if not ICD10_PATTERN.fullmatch(claim.diagnosisCode):
        apply_rule("invalid_icd10", 0.25, "Diagnosis code format is invalid")

    if not CPT_PATTERN.fullmatch(claim.cptCode):
        apply_rule("invalid_cpt", 0.25, "CPT code format is invalid")

    if claim.provider.upper() not in IN_NETWORK_PROVIDERS:
        apply_rule("provider_out_of_network", 0.08, "Provider not found in in-network reference list")

    if issues:
        issue_penalty = min(len(issues) * 0.06, 0.30)
        score += issue_penalty
        contributions.append(
            RiskContribution(
                rule="missing_or_derived_fields",
                delta=round(issue_penalty, 2),
                reason=f"{len(issues)} extraction issues contributed to risk",
            )
        )
        reasons.extend(issues)

    score = round(max(0.0, min(score, 1.0)), 2)

    model_info = RiskModelInfo(
        baseScore=base_score,
        maxIssuePenalty=0.30,
        issuePenaltyPerItem=0.06,
        thresholds={"lowMax": 0.30, "mediumMax": 0.60, "highMax": 1.00},
        contributions=contributions,
    )

    risk_label, recommendation = _risk_band(score)
    return score, risk_label, recommendation, reasons, contributions, model_info


def _extract_first_json_object(text: str) -> dict | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[index:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _build_llm_prompt(claim: ClaimData, issues: list[str]) -> str:
    payload = {
        "claimData": claim.model_dump(mode="json"),
        "extractionIssues": issues,
        "knownInNetworkProviders": sorted(IN_NETWORK_PROVIDERS),
        "scoringHint": {
            "riskScoreRange": [0, 1],
            "riskBands": {"LOW": "<=0.30", "MEDIUM": "<=0.60", "HIGH": ">0.60"},
            "recommendations": ["APPROVE", "REVIEW", "REJECT"],
        },
    }
    return (
        "You are a medical claim risk assessor. "
        "Return only JSON with this exact schema: "
        "{\n"
        '  "riskScore": number between 0 and 1,\n'
        '  "riskLabel": "LOW"|"MEDIUM"|"HIGH",\n'
        '  "recommendation": "APPROVE"|"REVIEW"|"REJECT",\n'
        '  "reasons": [string],\n'
        '  "contributions": [{"rule": string, "delta": number, "reason": string}]\n'
        "}\n"
        "The reasons must reference concrete claim fields and extraction issues.\n"
        f"Input:\n{json.dumps(payload)}"
    )


@lru_cache(maxsize=128)
def _call_llm_chat_cached(
    base_url: str,
    model_name: str,
    api_key: str,
    timeout_s: float,
    prompt: str,
) -> dict | None:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model_name,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You output strict JSON only for claim risk scoring.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(f"{base_url}/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


def _calculate_risk_llm(
    claim: ClaimData,
    issues: list[str],
) -> tuple[float, str, str, list[str], list[RiskContribution], RiskModelInfo] | None:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return None

    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    timeout_s = float(os.getenv("LLM_TIMEOUT_SECONDS", "15"))

    payload = _call_llm_chat_cached(
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        timeout_s=timeout_s,
        prompt=_build_llm_prompt(claim, issues),
    )
    if payload is None:
        return None

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None

    if not isinstance(content, str):
        return None

    parsed = _extract_first_json_object(content)
    if not parsed:
        return None

    try:
        raw_score = float(parsed.get("riskScore", 0.5))
    except (TypeError, ValueError):
        return None

    score = round(max(0.0, min(raw_score, 1.0)), 2)
    risk_label = str(parsed.get("riskLabel", "")).upper()
    recommendation = str(parsed.get("recommendation", "")).upper()

    if risk_label not in {"LOW", "MEDIUM", "HIGH"} or recommendation not in {"APPROVE", "REVIEW", "REJECT"}:
        risk_label, recommendation = _risk_band(score)

    reasons_raw = parsed.get("reasons", [])
    reasons = [str(item) for item in reasons_raw if isinstance(item, str) and item.strip()]
    if not reasons:
        reasons = ["LLM did not provide detailed reasons."]

    contributions_raw = parsed.get("contributions", [])
    contributions: list[RiskContribution] = []
    if isinstance(contributions_raw, list):
        for row in contributions_raw:
            if not isinstance(row, dict):
                continue
            rule = str(row.get("rule", "llm_rule"))
            reason = str(row.get("reason", "No contribution reason provided"))
            try:
                delta = float(row.get("delta", 0))
            except (TypeError, ValueError):
                delta = 0.0
            contributions.append(
                RiskContribution(rule=rule, delta=round(delta, 2), reason=reason)
            )

    model_info = RiskModelInfo(
        engine="llm",
        modelName=model_name,
        baseScore=0.0,
        maxIssuePenalty=0.0,
        issuePenaltyPerItem=0.0,
        thresholds={"lowMax": 0.30, "mediumMax": 0.60, "highMax": 1.00},
        contributions=contributions,
    )

    return score, risk_label, recommendation, reasons, contributions, model_info


def _calculate_risk(
    claim: ClaimData,
    issues: list[str],
) -> tuple[float, str, str, list[str], list[RiskContribution], RiskModelInfo]:
    score, risk_label, recommendation, reasons, contributions, model_info = _calculate_risk_rules(claim, issues)

    mode = (os.getenv("LLM_RISK_MODE", "hybrid") or "hybrid").strip().lower()
    if mode in {"off", "false", "0", "disabled"}:
        return score, risk_label, recommendation, reasons, contributions, model_info

    # Free-tier friendly default: only call LLM for borderline cases.
    if mode == "hybrid":
        max_issues = int(os.getenv("LLM_MAX_ISSUES_FOR_LLM", "3"))
        allowed_labels_raw = os.getenv("LLM_ALLOWED_LABELS", "MEDIUM")
        allowed_labels = {x.strip().upper() for x in allowed_labels_raw.split(",") if x.strip()}

        is_borderline = risk_label in allowed_labels
        has_reasonable_signal = claim.totalBilled > 0 and claim.cptCode != "00000" and claim.diagnosisCode != "UNKNOWN"
        has_acceptable_quality = len(issues) <= max_issues

        if not (is_borderline and has_reasonable_signal and has_acceptable_quality):
            return score, risk_label, recommendation, reasons, contributions, model_info

    llm_result = _calculate_risk_llm(claim, issues)
    if llm_result is not None:
        return llm_result

    return score, risk_label, recommendation, reasons, contributions, model_info

def _draft_email(claim: ClaimData, risk_label: str, recommendation: str, reasons: list[str]) -> str:
    reasons_block = "\n".join(f"- {r}" for r in reasons[:5]) or "- No notable risk signals"

    return f"""Subject: Claim Review Update — Policy #{claim.policyNumber}

Dear Policyholder,

Your medical claim has been processed by our autonomous claim pipeline.

Claim Summary:
- Date of Service: {claim.dateOfService.strftime('%B %d, %Y')}
- Provider: {claim.provider}
- Diagnosis: {claim.diagnosisDesc} ({claim.diagnosisCode})
- Total Billed: ${claim.totalBilled:,.2f}
- Approved Amount: ${claim.approvedAmount:,.2f}
- Patient Responsibility: ${claim.patientResponsibility:,.2f}

System Decision: {recommendation}
Risk Level: {risk_label}

Risk Signals:
{reasons_block}

If you have questions, please contact support and reference your policy number.

Best regards,
Binary Blitz Claim Agent
"""


def _draft_whatsapp(claim: ClaimData, recommendation: str, risk_label: str, risk_score: float) -> str:
    return (
        "Claim Status Update\n\n"
        f"Provider: {claim.provider}\n"
        f"Diagnosis: {claim.diagnosisCode}\n"
        f"Approved: ${claim.approvedAmount:,.2f}\n"
        f"Your Cost: ${claim.patientResponsibility:,.2f}\n"
        f"Decision: {recommendation} ({risk_label})\n"
        f"Risk Score: {risk_score:.2f}"
    )


def run_claim_pipeline(filename: str, file_bytes: bytes) -> ProcessResponse:
    _normalize_file_type(filename)

    text = _extract_text(filename, file_bytes)
    claim, issues = _extract_claim_data(text)
    risk_score, risk_label, recommendation, reasons, _, risk_model = _calculate_risk(claim, issues)

    return ProcessResponse(
        claimData=claim,
        riskScore=risk_score,
        riskLabel=risk_label,
        recommendation=recommendation,
        riskReasons=reasons,
        extractionIssues=issues,
        extractionTextPreview=text[:1200],
        riskModel=risk_model,
        email=_draft_email(claim, risk_label, recommendation, reasons),
        whatsapp=_draft_whatsapp(claim, recommendation, risk_label, risk_score),
    )
