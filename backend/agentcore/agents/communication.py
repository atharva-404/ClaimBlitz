"""Communication Agent — drafts outbound messages from the final decision.

Once the Judge has ruled, this agent drafts policyholder-facing communications
(approval / review-request) plus an internal note. It drafts strictly from the
final decision — never from a mix of raw analyst reasoning — and never states
or implies fraud. For a REVIEW outcome it uses the language "Additional
documentation is required before the claim can proceed." (design §8.7).

Exposes ``draft()`` for the Supervisor; returns a dict with keys
``email_draft``, ``sms_draft``, ``internal_note``, ``tone``, ``confidence``.
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, Evidence, EvidenceSource, Verdict


REVIEW_LANGUAGE = "Additional documentation is required before the claim can proceed."


class CommunicationAgent(Agent):
    """Draft outbound messages from the Judge's final decision."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Communication Agent in a medical insurance claim processing "
            "system. You draft clear, empathetic, professional communications to "
            "policyholders based ONLY on the final decision you are given.\n\n"
            "Hard rules:\n"
            "- Never state or imply fraud, suspicion, or wrongdoing.\n"
            "- For a REVIEW outcome, use language such as: "
            f'"{REVIEW_LANGUAGE}" and explain what is needed, without alarm.\n'
            "- For APPROVE, confirm the outcome plainly. For REJECT, give a factual, "
            "non-accusatory reason.\n"
            "- Draft from the decision only, not from internal analyst debate.\n\n"
            "You produce an email draft, an SMS draft, and an internal note.\n\n"
            "Respond with strict JSON:\n"
            '{"email_draft": "...", "sms_draft": "...", '
            '"internal_note": "...", "tone": "...", '
            '"confidence": 0.0-1.0}'
        )

    async def draft(
        self,
        *,
        claim_id: str,
        decision: str,
        reasoning: str,
        claim: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate outbound communication drafts from the final decision."""
        decision_label = str(decision).upper()
        review_hint = (
            f'\nFor a REVIEW decision, the email and SMS must convey: "{REVIEW_LANGUAGE}"'
            if decision_label in ("REVIEW", "FLAG")
            else ""
        )
        instructions = (
            f"Draft communications for claim {claim_id}.\n"
            f"Final decision: {decision_label}\n"
            f"Decision rationale: {reasoning}\n"
            f"{review_hint}\n\n"
            f"Create an email draft, an SMS draft, and an internal note. Do not state or "
            f"imply fraud. Base the message only on the final decision above."
        )
        result = await self.ask_llm_json(instructions, max_tokens=2000)
        parsed = result.parsed
        return parsed if isinstance(parsed, dict) else {}

    async def analyze(
        self,
        *,
        claim_id: str,
        claim: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentFinding:
        decision = claim.get("decision", "pending")
        reasoning = claim.get("reasoning", "")
        drafts = await self.draft(
            claim_id=claim_id,
            decision=decision,
            reasoning=reasoning,
            claim=claim,
        )

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=Verdict.APPROVE,
            confidence=self.make_confidence(
                drafts.get("confidence", 0.85) if isinstance(drafts, dict) else 0.85,
                "Communication drafts generated",
            ),
            reasoning="Drafts generated for policyholder communication",
            evidence=[
                Evidence(
                    source=EvidenceSource.PEER_AGENT,
                    snippet=f"Decision: {decision}",
                )
            ],
            tags=["drafts_ready"],
        )


__all__ = ["CommunicationAgent"]
