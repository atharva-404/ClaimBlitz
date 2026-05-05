from __future__ import annotations

from contracts import ClaimData
from services.llm_client import get_llm_client
from utils.normalizers import to_float, to_int, to_str, to_str_list


def run_doc_reader(pdf_text: str) -> dict:
    prompt = (
        "You are a medical document extraction agent for Indian hospitals.\n"
        "Extract the following fields from this hospital discharge summary and return ONLY a valid JSON object with no explanation, no markdown, no backticks.\n\n"
        "Fields to extract:\n"
        "- patient_name (string)\n"
        "- patient_age (number)\n"
        "- dob (string, DD/MM/YYYY format)\n"
        "- gender (string)\n"
        "- diagnosis (string — primary diagnosis in plain English)\n"
        "- icd_codes (array of strings — ICD-10 codes, e.g. [\"J18.9\", \"E11.9\"])\n"
        "- procedures (array of strings — medical procedures performed)\n"
        "- total_cost (number — in INR rupees, numeric only)\n"
        "- room_charges (number — INR)\n"
        "- medicine_charges (number — INR)\n"
        "- doctor_charges (number — INR)\n"
        "- admission_date (string, DD/MM/YYYY)\n"
        "- discharge_date (string, DD/MM/YYYY)\n"
        "- hospital_name (string)\n"
        "- doctor_name (string)\n"
        "- policy_number (string or null if not present)\n"
        "- pre_auth_number (string or null if not present)\n"
        "- tpa_name (string — e.g. \"NIVA BUPA\", \"Star Health\" or null)\n\n"
        "Set any missing field to null. Return ONLY the JSON.\n\n"
        f"DISCHARGE SUMMARY TEXT:\n{pdf_text[:30000]}"
    )

    raw = get_llm_client().call_json(prompt=prompt, max_tokens=1500)

    claim = ClaimData(
        patient_name=to_str(raw.get("patient_name")),
        patient_age=to_int(raw.get("patient_age")),
        dob=to_str(raw.get("dob")),
        gender=to_str(raw.get("gender")),
        diagnosis=to_str(raw.get("diagnosis")),
        icd_codes=to_str_list(raw.get("icd_codes")),
        procedures=to_str_list(raw.get("procedures")),
        total_cost=to_float(raw.get("total_cost")),
        room_charges=to_float(raw.get("room_charges")),
        medicine_charges=to_float(raw.get("medicine_charges")),
        doctor_charges=to_float(raw.get("doctor_charges")),
        admission_date=to_str(raw.get("admission_date")),
        discharge_date=to_str(raw.get("discharge_date")),
        hospital_name=to_str(raw.get("hospital_name")),
        doctor_name=to_str(raw.get("doctor_name")),
        policy_number=to_str(raw.get("policy_number")),
        pre_auth_number=to_str(raw.get("pre_auth_number")),
        tpa_name=to_str(raw.get("tpa_name")),
    )

    return claim.model_dump()
