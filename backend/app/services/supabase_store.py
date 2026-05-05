import os
from datetime import datetime, timezone
from functools import lru_cache

from supabase import Client, create_client

from app.models import ProcessResponse


class SupabaseConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url or not key:
        raise SupabaseConfigError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to persist claims."
        )

    return create_client(url, key)


def persist_claim_result(result: ProcessResponse, source_file: str) -> None:
    client = _get_supabase_client()
    table = os.getenv("SUPABASE_TABLE", "claims").strip() or "claims"

    payload = {
        "source_file": source_file,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "patient_name": result.claimData.patientName,
        "policy_number": result.claimData.policyNumber,
        "provider": result.claimData.provider,
        "diagnosis_code": result.claimData.diagnosisCode,
        "cpt_code": result.claimData.cptCode,
        "total_billed": result.claimData.totalBilled,
        "approved_amount": result.claimData.approvedAmount,
        "patient_responsibility": result.claimData.patientResponsibility,
        "risk_score": result.riskScore,
        "risk_label": result.riskLabel,
        "recommendation": result.recommendation,
        "email_draft": result.email,
        "whatsapp_draft": result.whatsapp,
        "claim_json": result.model_dump(mode="json"),
    }

    client.table(table).insert(payload).execute()
