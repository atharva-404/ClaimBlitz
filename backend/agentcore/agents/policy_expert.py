"""Policy Expert Agent — grounded coverage, no invented clauses.

Determines coverage ONLY from an actual policy document / structured policy
data. If no policy document is present (``policy_status != PRESENT``), the
agent short-circuits BEFORE calling the LLM and returns
``coverage_status = INSUFFICIENT_EVIDENCE`` with ``verdict = FLAG`` and the
list of missing policy info — it never assumes covered/excluded and never
fabricates clause text (design §8.3).
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..claim_model import CoverageStatus, PolicyStatus
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


# Coverage-term fields a reviewer needs an actual policy document to assess.
_MISSING_POLICY_INFO = (
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
)


class PolicyExpertAgent(Agent):
    """Grounded policy coverage assessment."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Policy Expert Agent in a medical insurance claim processing system. "
            "You determine coverage ONLY from an actual policy document or structured policy "
            "data that is present in the Master Claim Form. You must NEVER assume a claim is "
            "covered or excluded, and you must NEVER fabricate policy clause text.\n\n"
            "If the policy terms needed to decide coverage are not present, return "
            "coverage_status INSUFFICIENT_EVIDENCE and list what is missing. Otherwise, cite "
            "the specific policy evidence (snippet + page) behind your conclusion.\n\n"
            "Respond with strict JSON:\n"
            '{"coverage_status": "COVERED|NOT_COVERED|PARTIALLY_COVERED|'
            'INSUFFICIENT_EVIDENCE|HUMAN_REVIEW", '
            '"coverage_evidence": [{"snippet": "...", "page": n}], '
            '"relevant_clause": null, '
            '"missing_policy_info": ["sum_insured", "exclusions"], '
            '"confidence": 0.0-1.0, "reasoning": "policy assessment"}'
        )

    async def answer_question(
        self, *, claim_id: str, question: str, context: dict[str, Any] | None = None
    ) -> str:
        """Answer peer questions about policy coverage rules."""
        instructions = (
            f"A peer agent asks about policy rules for claim {claim_id}: {question}\n\n"
            f"Context: {json.dumps(context or {}, default=str)}\n\n"
            f"Answer only from policy evidence present in the data; do not fabricate clauses."
        )
        result = await self.ask_llm_json(instructions)
        return result.parsed.get("answer", result.raw_text)

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        policy = claim.get("policy") or {}
        policy_status = policy.get("policy_status")

        # --- Code guard: short-circuit BEFORE the LLM when no policy doc ---
        if policy_status != PolicyStatus.PRESENT.value:
            missing = [
                attr
                for attr in _MISSING_POLICY_INFO
                if _is_missing(policy.get(attr))
            ]
            reasoning = (
                "No policy document is present; coverage cannot be determined without it. "
                "Routing to review."
            )
            return AgentFinding(
                agent=self.role,
                claim_id=claim_id,
                verdict=Verdict.FLAG,
                confidence=self.make_confidence(0.6, reasoning),
                reasoning=reasoning,
                evidence=[
                    Evidence(
                        source=EvidenceSource.POLICY_DB,
                        field="policy.policy_status",
                        snippet=f"policy_status={policy_status}",
                    )
                ],
                referenced_fields=["policy.policy_status"],
                tags=[
                    f"coverage_{CoverageStatus.INSUFFICIENT_EVIDENCE.value.lower()}",
                    "policy_document_missing",
                ],
            )

        # --- Policy document present: grounded LLM assessment ---
        objection_note = ""
        if context and context.get("objection"):
            objection_note = (
                "\n\nReconsider after challenge: "
                f"{context['objection'].get('reason', '')}"
            )

        instructions = (
            f"Assess policy coverage for this Master Claim Form:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}"
            f"{objection_note}\n\n"
            f"Cite the policy evidence behind your conclusion; if terms are missing, say so."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        coverage_status = _safe_coverage(parsed.get("coverage_status"))
        conf_value = parsed.get("confidence", 0.7)
        reasoning = parsed.get("reasoning", "No reasoning provided")
        missing_info = parsed.get("missing_policy_info", []) or []
        coverage_evidence = parsed.get("coverage_evidence", []) or []

        # Only a positive, evidence-backed COVERED can approve; anything else
        # (not covered / partial / insufficient / human review) routes to FLAG.
        verdict = (
            Verdict.APPROVE
            if coverage_status == CoverageStatus.COVERED
            else Verdict.FLAG
        )

        await self.memory.remember(
            text=f"Claim {claim_id} policy: {coverage_status.value} - {reasoning[:120]}",
            metadata={"claim_id": claim_id, "coverage_status": coverage_status.value},
        )

        evidence: list[Evidence] = []
        for ev in coverage_evidence[:5]:
            if isinstance(ev, dict) and ev.get("snippet"):
                page = ev.get("page")
                evidence.append(
                    Evidence(
                        source=EvidenceSource.POLICY_DB,
                        field="policy",
                        snippet=str(ev["snippet"])[:200],
                        citation=f"page {page}" if isinstance(page, int) else None,
                    )
                )

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["policy.policy_status", "policy.coverage_type"],
            tags=[f"coverage_{coverage_status.value.lower()}"]
            + [f"missing_{m}" for m in missing_info[:4]],
        )


def _is_missing(cell: Any) -> bool:
    if not isinstance(cell, dict):
        return cell is None
    return cell.get("status") == "MISSING" or cell.get("value") in (None, "")


def _safe_coverage(value: Any) -> CoverageStatus:
    try:
        return CoverageStatus(value)
    except (ValueError, TypeError):
        return CoverageStatus.INSUFFICIENT_EVIDENCE


__all__ = ["PolicyExpertAgent"]
