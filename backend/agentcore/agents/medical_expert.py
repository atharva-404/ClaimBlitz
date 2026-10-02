"""Clinical Consistency Agent — consistency, not medical truth.

Keeps ``AgentRole.MEDICAL_EXPERT`` (wire/DB compatibility) and the literal
"Medical Expert Agent" prompt marker (test mock key). Its display name is
"Clinical Consistency Agent" via ``AGENT_DISPLAY_NAMES``.

It assesses whether the claim's clinical narrative is internally consistent —
diagnosis vs documentation, symptoms/findings vs diagnosis, code consistency
only where a code is present, treatment vs documentation, procedure vs
diagnosis. It never asserts an unsupported medical conclusion: every finding
cites an evidence snippet from the form, and the agent abstains on any
sub-check that lacks evidence (design §8.2).
"""

from __future__ import annotations

import json
from typing import Any

from ..base import Agent
from ..protocol import AgentFinding, AgentRole, Evidence, EvidenceSource, Verdict


class MedicalExpertAgent(Agent):
    """Clinical consistency assessment (not medical adjudication)."""

    @property
    def system_prompt(self) -> str:
        # NB: the literal "Medical Expert Agent" marker substring is retained
        # for the test mock key, even though the display name is
        # "Clinical Consistency Agent".
        return (
            "You are the Medical Expert Agent (Clinical Consistency Agent) in a medical "
            "insurance claim processing system. You assess CONSISTENCY, not medical truth: "
            "you do not decide whether care was correct, only whether the claim's clinical "
            "narrative hangs together and is supported by the documentation provided.\n\n"
            "Assess these consistency sub-checks, each only where the relevant data is "
            "present in the Master Claim Form:\n"
            "- diagnosis <-> documentation (is the stated diagnosis supported by the recorded "
            "chief complaint / findings / history?)\n"
            "- symptoms/findings <-> diagnosis (do they align?)\n"
            "- diagnosis-code <-> diagnosis text (ONLY where a code is actually present)\n"
            "- treatment/medications <-> documentation\n"
            "- procedure <-> diagnosis\n\n"
            "Rules:\n"
            "- Cite an evidence snippet from the form for every finding. If evidence for a "
            "sub-check is absent, ABSTAIN on that sub-check rather than asserting.\n"
            "- Make no unsupported medical conclusions and never flag solely because a field "
            "is missing.\n\n"
            "Respond with strict JSON:\n"
            '{"verdict": "approve"|"flag"|"abstain", "confidence": 0.0-1.0, '
            '"reasoning": "consistency assessment", '
            '"checks": [{"check": "dx_doc|symptoms_dx|code_dx|treatment_doc|procedure_dx", '
            '"result": "consistent|inconsistent|not_evaluable", '
            '"evidence": "quoted snippet", "note": "..."}]}'
        )

    async def answer_question(
        self, *, claim_id: str, question: str, context: dict[str, Any] | None = None
    ) -> str:
        """Answer peer questions about clinical consistency."""
        instructions = (
            f"A peer agent asks about claim {claim_id}: {question}\n\n"
            f"Context: {json.dumps(context or {}, default=str)}\n\n"
            f"Answer strictly from the documented evidence. Cite the snippet you relied on."
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
        clinical = claim.get("clinical") or {}
        diagnosis = _cell_value(clinical.get("primary_diagnosis"))
        codes = _cell_value(clinical.get("diagnosis_codes"))

        # Memory recall kept (private per-agent capability).
        similar = await self.memory.recall(
            query=f"consistency: diagnosis={diagnosis} codes={codes}",
            top_k=3,
        )
        memory_context = ""
        if similar:
            memory_context = "\n\nSimilar past cases from memory:\n" + "\n".join(
                f"- {r.text} (score={r.score:.2f})" for r in similar
            )

        objection_note = ""
        if context and context.get("objection"):
            objection_note = (
                "\n\nYou previously assessed this claim and were challenged: "
                f"{context['objection'].get('reason', '')}. Reconsider carefully."
            )

        instructions = (
            f"Assess the clinical consistency of this Master Claim Form:\n\n"
            f"{json.dumps(claim, indent=2, default=str)}"
            f"{memory_context}{objection_note}\n\n"
            f"Evaluate each sub-check only where evidence is present; abstain otherwise."
        )
        result = await self.ask_llm_json(instructions)
        parsed = result.parsed

        verdict = _safe_verdict(parsed.get("verdict", "abstain"))
        conf_value = parsed.get("confidence", 0.7)
        reasoning = parsed.get("reasoning", "No reasoning provided")
        checks = parsed.get("checks", []) or []

        await self.memory.remember(
            text=f"Claim {claim_id} clinical consistency: {verdict.value} - {reasoning[:120]}",
            metadata={"claim_id": claim_id, "verdict": verdict.value},
        )

        evidence: list[Evidence] = []
        tags: list[str] = []
        for c in checks[:5]:
            if not isinstance(c, dict):
                continue
            check_name = c.get("check", "check")
            result_label = c.get("result", "not_evaluable")
            snippet = c.get("evidence", "")
            if result_label == "not_evaluable":
                tags.append(f"{check_name}_not_present")
                continue
            tags.append(f"{check_name}_{'consistent' if result_label == 'consistent' else 'inconsistent'}")
            # Only cite evidence that is actually quoted (no unsupported claims).
            if snippet:
                evidence.append(
                    Evidence(
                        source=EvidenceSource.DOCUMENT,
                        field="clinical",
                        snippet=str(snippet)[:200],
                        weight=1.0 if result_label == "inconsistent" else 0.5,
                    )
                )

        return AgentFinding(
            agent=self.role,
            claim_id=claim_id,
            verdict=verdict,
            confidence=self.make_confidence(conf_value, reasoning),
            reasoning=reasoning,
            evidence=evidence,
            referenced_fields=["clinical.primary_diagnosis", "clinical.diagnosis_codes"],
            tags=tags[:5],
        )


def _cell_value(cell: Any) -> Any:
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def _safe_verdict(value: Any) -> Verdict:
    try:
        v = Verdict(value)
    except ValueError:
        return Verdict.ABSTAIN
    # The consistency agent never REJECTs (not its domain); map to FLAG.
    if v == Verdict.REJECT:
        return Verdict.FLAG
    return v


_ = AgentRole  # keep AgentRole import referenced (role enum unchanged)

__all__ = ["MedicalExpertAgent"]
