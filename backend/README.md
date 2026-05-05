# Binary Blitz Backend

FastAPI backend for your Autonomous Medical Insurance Claim Agent.

## How Risk Is Calculated (No LLM)

This backend uses a deterministic rules engine, not an LLM.

Input basis:
- Extracted fields from uploaded PDF/image text
- Billing ratio (`approvedAmount / totalBilled`)
- Claim amount thresholds
- ICD-10 and CPT format checks
- Provider in-network lookup
- Missing-field penalties

Output:
- `riskScore` in range `[0, 1]`
- `riskLabel` (`LOW`, `MEDIUM`, `HIGH`)
- `recommendation` (`APPROVE`, `REVIEW`, `REJECT`)

## Endpoints

- `GET /health` -> service status
- `POST /process` -> claim processing (multipart file upload: `file`)

## OCR Notes

- PDF extraction is handled by `pypdf`.
- Image OCR uses `pytesseract` + `pillow`.
- For image OCR to work, Tesseract OCR engine must be installed on your machine.

## Supabase (Database)

This project can persist each processed claim to Supabase.

Setup:
1. Copy `.env.example` to `.env`.
2. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
3. Optionally set `SUPABASE_TABLE` (default: `claims`).

If Supabase is not configured, processing still works and only persistence is skipped.

Suggested table schema (`claims`):
- `id` uuid primary key default `gen_random_uuid()`
- `created_at` timestamptz not null
- `source_file` text
- `patient_name` text
- `policy_number` text
- `provider` text
- `diagnosis_code` text
- `cpt_code` text
- `total_billed` numeric
- `approved_amount` numeric
- `patient_responsibility` numeric
- `risk_score` numeric
- `risk_label` text
- `recommendation` text
- `email_draft` text
- `whatsapp_draft` text
- `claim_json` jsonb

Response shape is aligned to the frontend hook expectation in `frontend/src/hooks/useClaimAgent.js`.

## Run Locally

1. Create and activate a virtual environment
2. Install dependencies
3. Start uvicorn

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger docs will be available at `http://localhost:8000/docs`.
