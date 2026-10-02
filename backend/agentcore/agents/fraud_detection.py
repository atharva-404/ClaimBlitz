"""Fraud Detection Agent — real-signal only, never "high bill = fraud".

Separates risk types and forbids price-based conclusions. A code post-filter
drops any indicator whose only cited evidence is the bill-amount magnitude.
When no indicators survive, the reasoning is exactly
"No direct fraud evidence identified from supplied documents." and the fraud
verdict is APPROVE — the agent never forces a flag (design §8.4).
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


NO_EVIDENCE_REASONING = "No direct fraud evidence identified from supplied documents."

_RISK_TYPES = ("DATA_QUALITY", "FRAUD", "CLINICAL", "POLICY", "BILLING")

# Phrases that signal an indicator rests ONLY on bill-amount magnitude.
_AMOUNT_ONLY_PATTERNS = (
    r"high(?:er)?\s+(?:bill|amount|cost|charge|total)",
    r"(?:bill|amount|cost|charge|total)\s+(?:is\s+)?(?:too\s+)?high",
    r"expensive",
    r"large\s+(?:bill|amount|sum|total)",
    r"costly",
    r"exceeds?\s+(?:the\s+)?(?:average|norm|typical)",
    r"unusually\s+(?:high|large|expensive)",
)
_AMOUNT_ONLY_RE = re.compile("|".join(_AMOUNT_ONLY_PATTERNS), re.IGNORECASE)

# Concrete, non-price signal keywords that rescue an indicator from the filter.
_CONCRETE_SIGNAL_RE = re.compile(
    r"duplicate|conflict|mismatch|identity|date|admission|discharge|"
    r"unbundl|upcod|repeated|inconsistent|forg|manipulat|phantom",
    re.IGNORECASE,
)


class FraudDetectionAgent(Agent):
    """Fraud analysis from concrete signals only (never price magnitude)."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Fraud Detection Agent in a medical insurance claim processing system. "
            "You identify potential fraud, waste, or abuse — but ONLY from concrete signals "
            "present in the data. A high bill amount by itself is NEVER fraud and must never "
            "produce an indicator.\n\n"
            "Separate every indicator into a risk type: DATA_QUALITY, FRAUD, CLINICAL, POLICY, "
            "or BILLING. Legitimate concrete signals include: duplicate claim/bill numbers, "
            "conflicting patient/provider identity across documents, duplicate billing line "
            "items, inconsistent dates (admission after discharge, service after submission). "
            "Do NOT conclude fraud from price magnitude, and cite the specific evidence snippet "
            "for every indicator.\n\n"
            "Respond with strict JSON:\n"
            '{"fraud_indicators": [{"indicator": "...", "evidence": "snippet", '
            '"confidence": 0.0-1.0, "severity": "low|medium|high", '
            '"risk_type": "DATA_QUALITY|FRAUD|CLINICAL|POLICY|BILLING"}], '
            '"overall_fraud_assessment": "...", "confidence": 0.0-1.0}'
        )

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        provider = _cell_value((claim.get("provider") or {}).get("hospital_name"))
        diagnosis = _cell_value((claim.get("clinical") or {}).get("primary_diagnosis"))

        similar = await self.memory.recall(
            query=f"fraud pattern: provider={provider} diagnosis={diagnosis}",
            top_k=5,
        )
        memory_context = ""
        if similar:
            memory_context = "\n\nSimilar past cases from fraud memory:\n" + "\n".join(
                f"- {r.text} (similarity={r.score:.2f})" for r in similar
            )

        objection_note = ""
        if context and context.get("objection"):
            objection_note = (
                f"\n\nReconsider after challenge: {context['objection'].get('reason', '')}"
            )

        instructions = (
            f"Analyze this Master Claim Form for concrete fraud indicators:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}"
            f"{memory_context}{objection_note}\n\n"
            f"Remember: a high bill amount alone is never fraud. Cite concrete evidence."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        raw_indicators = parsed.get("fraud_indicators", []) or []
        surviving = [i for i in raw_indicators if self._survives_filter(i)]

        if not surviving:
            # Exact no-evidence message; fraud dimension APPROVEs (design §8.4).
            return AgentFinding(
                agent=self.role,
                claim_id=claim_id,
                verdict=Verdict.APPROVE,
                confidence=self.make_confidence(
                    parsed.get("confidence", 0.8), NO_EVIDENCE_REASONING
                ),
                reasoning=NO_EVIDENCE_REASONING,
                evidence=[],
                referenced_fields=["provider.hospital_name", "billing.line_items"],
                tags=["no_fraud_evidence"],
            )

        reasoning = parsed.get("overall_fraud_assessment") or (
            f"{len(surviving)} concrete fraud indicator(s) identified."
        )
        conf_value = parsed.get("confidence", 0.6)

        await self.memory.remember(
            text=(
                f"Claim {claim_id} fraud: {len(surviving)} indicator(s) "
                f"[{[i.get('indicator') for i in surviving]}]"
            ),
            metadata={"claim_id": claim_id, "indicator_count": len(surviving)},
        )

        evidence = [
            Evidence(
                source=EvidenceSource.RULE_ENGINE,
                field=str(i.get("risk_type", "FRAUD")),
                snippet=str(i.get("evidence") or i.get("indicator", ""))[:200],
                weight=1.0 if i.get("severity") == "high" else 0.6,
            )
            for i in surviving[:5]
        ]

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=Verdict.FLAG,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["provider.hospital_name", "billing.line_items"],
            tags=[str(i.get("risk_type", "fraud")).lower() for i in surviving[:5]],
        )

    # ------------------------------------------------------------------

    def _survives_filter(self, indicator: Any) -> bool:
        """Drop indicators whose only cited evidence is bill-amount magnitude."""
        if not isinstance(indicator, dict):
            return False
        text = " ".join(
            str(indicator.get(k, ""))
            for k in ("indicator", "evidence", "detail")
        )
        if not text.strip():
            return False
        # If the citation names a concrete non-price signal, keep it.
        if _CONCRETE_SIGNAL_RE.search(text):
            return True
        # Otherwise, drop it when it reads as an amount-only conclusion.
        if _AMOUNT_ONLY_RE.search(text):
            return False
        return True


def _cell_value(cell: Any) -> Any:
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


__all__ = ["FraudDetectionAgent"]
