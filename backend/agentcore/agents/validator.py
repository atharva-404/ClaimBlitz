"""Validator Agent — categorized, evidence-grounded structural checks.

Validates the Master Claim Form for completeness, format correctness, and
internal consistency across six categories. It does NOT assess clinical
plausibility or policy coverage — those are other agents' domains.

The LLM proposes categorized findings; deterministic code checks (billing
recompute, date sanity, jurisdiction-aware coding, missing-document severity)
are merged in so the result is reproducible and never claims a field is
present unless the Master Claim Form marks it EXTRACTED/VERIFIED. The Validator
never REJECTs on completeness gaps — blocking conditions and the REVIEW outcome
are owned by Risk/Judge (design §8.1).
"""

from __future__ import annotations

import json
from typing import Any

import sys
from pathlib import Path

_BACKEND_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from utils.normalizers import to_float  # noqa: E402

from ..base import Agent  # noqa: E402
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict  # noqa: E402


_CATEGORIES = (
    "DOCUMENT_VALIDITY",
    "DATA_COMPLETENESS",
    "DATA_CONSISTENCY",
    "CODING",
    "BILLING",
    "DOCUMENT_CONSISTENCY",
)


class ValidatorAgent(Agent):
    """Structural/consistency validation of the Master Claim Form."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Validator Agent in a medical insurance claim processing system. "
            "Your job is to check the extracted claim data for structural correctness and "
            "internal consistency. You do NOT assess medical plausibility or policy coverage "
            "— those are other agents' domains.\n\n"
            "You receive a provenance-tagged Master Claim Form: every scalar carries a "
            "status (EXTRACTED, VERIFIED, MISSING, LOW_CONFIDENCE, CONFLICT). NEVER claim a "
            "field is present unless its status is EXTRACTED or VERIFIED. Report findings in "
            "these six categories:\n"
            "- DOCUMENT_VALIDITY: missing/invalid supporting documents\n"
            "- DATA_COMPLETENESS: required fields that are MISSING\n"
            "- DATA_CONSISTENCY: internal contradictions (dates, identities)\n"
            "- CODING: diagnosis/procedure/NPI code format and presence\n"
            "- BILLING: line-item math, duplicates, negative/non-numeric amounts\n"
            "- DOCUMENT_CONSISTENCY: cross-document conflicts (CONFLICT fields)\n\n"
            "Jurisdiction matters: a missing NPI or CPT code in a non-US claim is at most "
            "'info', never an error. Each finding must cite an evidence snippet.\n\n"
            "Respond with strict JSON:\n"
            '{"findings": [{"category": "DOCUMENT_VALIDITY|DATA_COMPLETENESS|'
            'DATA_CONSISTENCY|CODING|BILLING|DOCUMENT_CONSISTENCY", '
            '"severity": "error|warning|info", "field": "...", "message": "...", '
            '"evidence": "quoted snippet"}], '
            '"confidence": 0.0-1.0, "summary": "short overall assessment"}'
        )

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        instructions = (
            f"Validate the following Master Claim Form:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}\n\n"
            f"Report categorized findings with severity and evidence. Remember: a field is "
            f"only present if its status is EXTRACTED or VERIFIED; do not invent presence."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        # LLM-proposed findings, kept only when well-formed and categorized.
        findings: list[dict[str, Any]] = []
        for f in parsed.get("findings", []) or []:
            if not isinstance(f, dict):
                continue
            category = f.get("category")
            if category not in _CATEGORIES:
                continue
            severity = f.get("severity", "info")
            if severity not in ("error", "warning", "info"):
                severity = "info"
            findings.append(
                {
                    "category": category,
                    "severity": severity,
                    "field": f.get("field", ""),
                    "message": f.get("message", ""),
                    "evidence": f.get("evidence", ""),
                }
            )

        # Deterministic code checks merged in (reproducible, not LLM-dependent).
        findings.extend(self._deterministic_checks(claim))

        errors = [f for f in findings if f["severity"] == "error"]
        warnings = [f for f in findings if f["severity"] == "warning"]
        infos = [f for f in findings if f["severity"] == "info"]

        # Verdict mapping (design §8.1): any error/warning -> FLAG; clean or
        # info-only -> APPROVE. The Validator NEVER returns REJECT.
        if errors or warnings:
            verdict = Verdict.FLAG
        else:
            verdict = Verdict.APPROVE

        conf_value = parsed.get("confidence", 0.85)
        summary = parsed.get("summary") or (
            f"{len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info"
        )

        evidence = [
            Evidence(
                source=EvidenceSource.RULE_ENGINE,
                field=f.get("field", ""),
                snippet=f.get("evidence") or f.get("message", ""),
                weight=1.0 if f["severity"] == "error" else (0.6 if f["severity"] == "warning" else 0.3),
            )
            for f in findings[:8]
        ]

        tags = [f"{len(errors)}_errors", f"{len(warnings)}_warnings"]
        tags += [f["category"].lower() for f in (errors + warnings)[:4]]

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, summary),
            reasoning=summary,
            evidence=evidence,
            referenced_fields=[f.get("field", "") for f in findings if f.get("field")],
            tags=tags,
        )

    # ------------------------------------------------------------------
    # Deterministic checks (design §8.1)
    # ------------------------------------------------------------------

    def _deterministic_checks(self, claim: dict[str, Any]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        checks.extend(self._check_completeness(claim))
        checks.extend(self._check_billing(claim))
        checks.extend(self._check_consistency(claim))
        checks.extend(self._check_coding(claim))
        checks.extend(self._check_documents(claim))
        return checks

    def _check_completeness(self, claim: dict[str, Any]) -> list[dict[str, Any]]:
        """List MISSING fields as info (completeness is never an error)."""
        out: list[dict[str, Any]] = []
        for section_name in ("patient", "clinical", "hospitalization", "billing"):
            section = claim.get(section_name)
            if not isinstance(section, dict):
                continue
            for attr, cell in section.items():
                if not isinstance(cell, dict) or "status" not in cell:
                    continue
                if cell.get("status") == "MISSING":
                    out.append(
                        {
                            "category": "DATA_COMPLETENESS",
                            "severity": "info",
                            "field": f"{section_name}.{attr}",
                            "message": f"{section_name}.{attr} is MISSING",
                            "evidence": "status=MISSING",
                        }
                    )
        return out

    def _check_billing(self, claim: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        billing = claim.get("billing")
        if not isinstance(billing, dict):
            return out

        flag = billing.get("flag")
        if flag == "BILLING_MISMATCH":
            diff = billing.get("billing_difference")
            out.append(
                {
                    "category": "BILLING",
                    "severity": "error",
                    "field": "billing.submitted_total",
                    "message": f"Billing total mismatch (difference={diff}).",
                    "evidence": f"calculated={billing.get('calculated_total')}, "
                    f"submitted={_cell_value(billing.get('submitted_total'))}",
                }
            )

        # Duplicate / negative / non-numeric line items.
        lines = billing.get("line_items") or []
        seen: set[tuple[Any, Any]] = set()
        for i, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            amount_val = _cell_value(line.get("amount"))
            category_val = _cell_value(line.get("category"))
            num = to_float(amount_val)
            if amount_val is not None and num is None:
                out.append(
                    {
                        "category": "BILLING",
                        "severity": "error",
                        "field": f"billing.line_items[{i}].amount",
                        "message": "Non-numeric billing amount.",
                        "evidence": str(amount_val),
                    }
                )
            elif num is not None and num <= 0:
                out.append(
                    {
                        "category": "BILLING",
                        "severity": "warning",
                        "field": f"billing.line_items[{i}].amount",
                        "message": "Non-positive billing amount.",
                        "evidence": str(amount_val),
                    }
                )
            key = (category_val, num)
            if num is not None and category_val is not None and key in seen:
                out.append(
                    {
                        "category": "BILLING",
                        "severity": "warning",
                        "field": f"billing.line_items[{i}]",
                        "message": "Duplicate billing line (same category and amount).",
                        "evidence": f"{category_val}={amount_val}",
                    }
                )
            seen.add(key)
        return out

    def _check_consistency(self, claim: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        hosp = claim.get("hospitalization") or {}
        admission = _cell_value(hosp.get("admission_date"))
        discharge = _cell_value(hosp.get("discharge_date"))
        if admission and discharge and str(admission) > str(discharge):
            out.append(
                {
                    "category": "DATA_CONSISTENCY",
                    "severity": "error",
                    "field": "hospitalization.admission_date",
                    "message": "Admission date is after discharge date.",
                    "evidence": f"admission={admission}, discharge={discharge}",
                }
            )

        # Policyholder vs patient name (only when both present).
        patient_name = _cell_value((claim.get("patient") or {}).get("name"))
        policyholder = _cell_value((claim.get("policy") or {}).get("policyholder_name"))
        if (
            patient_name
            and policyholder
            and str(patient_name).strip().lower() != str(policyholder).strip().lower()
        ):
            out.append(
                {
                    "category": "DATA_CONSISTENCY",
                    "severity": "info",
                    "field": "policy.policyholder_name",
                    "message": "Policyholder name differs from patient name.",
                    "evidence": f"patient={patient_name}, policyholder={policyholder}",
                }
            )

        # Diagnosis present but no code (info only).
        clinical = claim.get("clinical") or {}
        diagnosis = _cell_value(clinical.get("primary_diagnosis"))
        codes = _cell_value(clinical.get("diagnosis_codes"))
        if diagnosis and not codes:
            out.append(
                {
                    "category": "DATA_CONSISTENCY",
                    "severity": "info",
                    "field": "clinical.diagnosis_codes",
                    "message": "Diagnosis present without a diagnosis code.",
                    "evidence": str(diagnosis),
                }
            )

        # Any CONFLICT field -> error (DOCUMENT_CONSISTENCY).
        for path, status in _iter_statuses(claim):
            if status == "CONFLICT":
                out.append(
                    {
                        "category": "DOCUMENT_CONSISTENCY",
                        "severity": "error",
                        "field": path,
                        "message": "Conflicting values across source documents.",
                        "evidence": "status=CONFLICT",
                    }
                )
        return out

    def _check_coding(self, claim: dict[str, Any]) -> list[dict[str, Any]]:
        """Jurisdiction-aware: CPT/NPI absence is only an error where required."""
        out: list[dict[str, Any]] = []
        jurisdiction = claim.get("jurisdiction") or {}
        npi_required = bool(jurisdiction.get("npi_required"))
        coding_required = bool(jurisdiction.get("procedure_coding_required"))

        provider = claim.get("provider") or {}
        npi_cell = provider.get("npi")
        npi_missing = not isinstance(npi_cell, dict) or npi_cell.get("status") == "MISSING"
        if npi_missing:
            out.append(
                {
                    "category": "CODING",
                    "severity": "error" if npi_required else "info",
                    "field": "provider.npi",
                    "message": "NPI not present.",
                    "evidence": f"npi_required={npi_required}",
                }
            )

        clinical = claim.get("clinical") or {}
        codes = _cell_value(clinical.get("diagnosis_codes"))
        if coding_required and not codes:
            out.append(
                {
                    "category": "CODING",
                    "severity": "error",
                    "field": "clinical.diagnosis_codes",
                    "message": "Procedure/diagnosis coding required but absent.",
                    "evidence": f"procedure_coding_required={coding_required}",
                }
            )
        return out

    def _check_documents(self, claim: dict[str, Any]) -> list[dict[str, Any]]:
        """Missing policy/identity documents are warnings (drive FLAG)."""
        out: list[dict[str, Any]] = []
        docs = claim.get("supporting_documents") or {}
        for name in ("policy_document", "identity_document"):
            entry = docs.get(name)
            present = isinstance(entry, dict) and bool(entry.get("present"))
            if not present:
                out.append(
                    {
                        "category": "DOCUMENT_VALIDITY",
                        "severity": "warning",
                        "field": f"supporting_documents.{name}",
                        "message": f"{name.replace('_', ' ').title()} is not included.",
                        "evidence": "present=false",
                    }
                )
        return out


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _cell_value(cell: Any) -> Any:
    """Pull ``value`` out of a {value,status,...} provenance cell, or bare value."""
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def _iter_statuses(claim: dict[str, Any]) -> list[tuple[str, str]]:
    """Yield (dotted_path, status) for every provenance cell in the form dict."""
    out: list[tuple[str, str]] = []
    for section_name, section in claim.items():
        if not isinstance(section, dict):
            continue
        for attr, cell in section.items():
            if isinstance(cell, dict) and "status" in cell and "value" in cell:
                out.append((f"{section_name}.{attr}", cell.get("status")))
    return out


__all__ = ["ValidatorAgent"]
