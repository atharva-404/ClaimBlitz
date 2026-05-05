from __future__ import annotations

import json

from contracts import CommunicationOutput
from services.llm_client import get_llm_client
from utils.normalizers import to_str


def run_comm_agent(claim: dict, validation: dict) -> dict:
    prompt = (
        "You are a professional medical billing assistant at an Indian hospital.\n"
        "Write two communications for this insurance claim submission.\n\n"
        "1. A formal email to the TPA (NIVA BUPA) following up on a submitted claim. "
        "Use professional tone, include all key claim details, be concise.\n"
        "2. A short WhatsApp message to the patient informing them their claim has been submitted. "
        "Warm, reassuring tone. Max 2 sentences. In Hinglish is fine.\n\n"
        "Return ONLY this JSON:\n"
        "{\n"
        "  \"email_subject\": \"...\",\n"
        "  \"email_body\": \"...\",\n"
        "  \"whatsapp_message\": \"...\"\n"
        "}\n\n"
        f"Claim details:\n{json.dumps(claim, indent=2)}\n\n"
        f"Validation summary:\n{json.dumps(validation, indent=2)}"
    )

    raw = get_llm_client().call_json(prompt=prompt, max_tokens=1000)

    comms = CommunicationOutput(
        email_subject=to_str(raw.get("email_subject")) or "Insurance Claim Submission Follow-up",
        email_body=to_str(raw.get("email_body")) or "Please find the claim details attached for review.",
        whatsapp_message=to_str(raw.get("whatsapp_message")) or "Your insurance claim has been submitted.",
    )

    return comms.model_dump()
