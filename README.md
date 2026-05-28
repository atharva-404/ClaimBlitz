# ClaimBlitz - Autonomous Medical Insurance Claim Agent

<div align="center">
  <img src="https://img.shields.io/badge/Status-Active%20Development-informational?style=flat-square" alt="Status: Active Development" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License: MIT" />
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-0.116.1-009688?style=flat-square" alt="FastAPI 0.116.1" />
  <img src="https://img.shields.io/badge/React-18.3.1-61dafb?style=flat-square" alt="React 18.3.1" />
  <img src="https://img.shields.io/badge/Vite-8.0.4-646cff?style=flat-square" alt="Vite 8.0.4" />
</div>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [API Documentation](#api-documentation)
- [Claim Processing Workflow](#claim-processing-workflow)
- [Risk Scoring Model](#risk-scoring-model)
- [Database and Persistence](#database-and-persistence)
- [Frontend Experience](#frontend-experience)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**ClaimBlitz** is an autonomous medical insurance claim processing platform. It accepts a medical claim document, extracts claim data, validates important fields, calculates an explainable risk score, recommends an action, and generates patient or insurer communication drafts.

The project was originally built as **Binary Blitz** for a hackathon and is now organized as an end-to-end claim operations prototype with a FastAPI backend and a React/Vite frontend.

### Mission

Reduce manual insurance claim review effort by turning messy claim documents into structured, explainable, submission-ready outputs in seconds.

### What It Does

- Upload PDF, PNG, JPG, or JPEG claim documents.
- Extract medical, provider, policy, diagnosis, procedure, and billing fields.
- Detect missing or suspicious values.
- Score claim risk from `0` to `1`.
- Return a risk band: `LOW`, `MEDIUM`, or `HIGH`.
- Return a recommendation: `APPROVE`, `REVIEW`, or `REJECT`.
- Generate an email draft and WhatsApp-style update.
- Store the latest processed claim in browser local storage for portal handoff.
- Optionally persist claim results to Supabase.
- Simulate insurer portal submission with auto-filled clone pages.

---

## Key Features

### Claim Intake

- **Document Upload** - Supports `.pdf`, `.png`, `.jpg`, and `.jpeg` files.
- **Digital PDF Parsing** - Uses `pypdf` to extract embedded text from PDFs.
- **Scanned PDF Fallback** - Uses PyMuPDF and Tesseract OCR when PDF text is unavailable.
- **Image OCR** - Uses Pillow and Tesseract OCR for image-based claim documents.
- **Demo Mode** - Frontend can run a built-in demo payload without a file upload.

### Structured Claim Extraction

Extracts and normalizes:

- Patient name
- Date of birth
- Policy number
- Diagnosis code
- Diagnosis description
- CPT/procedure code
- Provider/hospital/clinic name
- Total billed amount
- Approved amount
- Patient responsibility
- Date of service

### Explainable Risk Intelligence

- Rules-first deterministic scoring.
- Optional OpenAI-compatible LLM scoring for selected borderline cases.
- Contribution-level explanation for each rule or model signal.
- Extraction issue tracking for missing or derived fields.
- Clear thresholds for approval, review, and rejection.

### Agentic Frontend Experience

The UI presents the pipeline as four visible agents:

- **Scanner Agent** - Uploads document and extracts structured data.
- **Validator Agent** - Checks consistency, ICD/CPT codes, and field quality.
- **Risk Analyst** - Computes risk score and final recommendation.
- **Comm Agent** - Generates communication drafts.

### Submission Workflow

- Saves the latest processed claim snapshot to local storage.
- Provides a **Claim Submission Hub**.
- Opens insurer portal clone pages.
- Auto-fills claim forms from extracted data.
- Generates a demo application number in the portal flow.

---

## Tech Stack

### Frontend

| Technology | Version | Purpose |
| --- | --- | --- |
| React | 18.3.1 lockfile | UI framework |
| Vite | ^8.0.4 | Dev server and build tool |
| TypeScript | ~6.0.2 | Build-time type tooling |
| React Router DOM | ^7.14.1 | Client-side routing |
| Framer Motion | ^12.38.0 | UI transitions and animation |
| Lucide React | ^1.8.0 | Icons |
| Recharts | ^3.8.1 | Charts and visualization |
| React Circular Progressbar | ^2.2.0 | Risk meter visualization |
| Tailwind CSS | ^4.2.2 | Styling utility system |
| Vitest | ^1.0.4 | Frontend tests |
| Testing Library React | ^14.1.2 | Hook/component testing |

### Backend

| Technology | Version | Purpose |
| --- | --- | --- |
| Python | 3.11+ recommended | Runtime |
| FastAPI | 0.116.1 | API framework |
| Uvicorn | 0.35.0 | ASGI server |
| Pydantic | 2.11.7 | Request/response models |
| pypdf | 5.9.0 | PDF text extraction |
| PyMuPDF | 1.26.4 | Scanned PDF rendering for OCR |
| Pillow | 11.3.0 | Image loading |
| pytesseract | 0.3.13 | OCR wrapper |
| Supabase Python | 2.7.4 | Optional claim persistence |
| httpx | 0.27.2 | Optional LLM API calls |
| pytest | 7.4.3 | Backend tests |

---

## Project Structure

```text
ClaimBlitz/
+-- backend/
|   +-- app/
|   |   +-- main.py                    # Active FastAPI app used by the frontend
|   |   +-- models.py                  # Pydantic response and claim models
|   |   +-- services/
|   |       +-- pipeline.py            # Extraction, risk scoring, drafts
|   |       +-- supabase_store.py      # Optional Supabase persistence
|   +-- agents/                        # Legacy/experimental multi-agent modules
|   |   +-- comm_agent.py
|   |   +-- doc_reader.py
|   |   +-- form_filler.py
|   |   +-- validator.py
|   +-- services/
|   |   +-- llm_client.py              # Gemini/Ollama helper for legacy agent app
|   +-- utils/
|   |   +-- json_cleaner.py
|   |   +-- normalizers.py
|   |   +-- pdf_parser.py
|   +-- tests/
|   |   +-- test_process_endpoint.py   # Backend regression tests
|   +-- test_data/                     # Sample PDFs and generators
|   +-- sample_data/                   # Sample data docs
|   +-- .env.example                   # Backend environment template
|   +-- requirements.txt               # Python dependencies
|   +-- README.md                      # Backend-specific documentation
|
+-- frontend/
|   +-- src/
|   |   +-- components/
|   |   |   +-- AgentStepper.jsx       # Agent progress UI
|   |   |   +-- DocumentViewer.jsx     # Upload and document state UI
|   |   |   +-- OutputSection.jsx      # Claim output and drafts
|   |   |   +-- RiskMeter.jsx          # Risk visualization
|   |   |   +-- TerminalWindow.jsx     # Pipeline logs
|   |   +-- hooks/
|   |   |   +-- useClaimAgent.js       # Frontend pipeline state + API call
|   |   |   +-- __tests__/             # Hook tests
|   |   +-- pages/
|   |   |   +-- Dashboard.jsx          # Main claim processing dashboard
|   |   |   +-- InsurerPortalPage.jsx  # Auto-fill portal clone
|   |   |   +-- LandingPage.jsx        # Product landing page
|   |   |   +-- SubmissionPage.jsx     # Submission hub
|   |   +-- App.jsx                    # Routes
|   |   +-- main.jsx                   # React entry point
|   |   +-- index.css                  # Tailwind/global styles
|   |   +-- style.css                  # Additional styles
|   +-- package.json                   # Frontend scripts and dependencies
|   +-- vite.config.js                 # Vite config
|   +-- vitest.config.js               # Vitest config
|   +-- tsconfig.json                  # TypeScript config
|
+-- BINARY_BLITZ_AGENT_BRIEF.md        # Hackathon/project brief
+-- HACKATHON_MASTER_PITCH.md          # Demo and pitch guide
+-- TESTING.md                         # Testing instructions
+-- TEST_RESULTS.md                    # Test result notes
+-- test_claim.pdf                     # Root sample claim PDF
+-- LICENSE                            # MIT license
+-- README.md                          # Main project documentation
```

---

## Prerequisites

Install the following before running the project:

- **Python 3.11+**
- **Node.js 18+**
- **npm 9+**
- **Tesseract OCR** for image/scanned PDF OCR
- **Supabase account** only if persistence is required
- **OpenAI-compatible LLM API key** only if optional LLM scoring is required

### Tesseract OCR Notes

On Windows, the backend checks common install paths:

```text
C:/Program Files/Tesseract-OCR/tesseract.exe
C:/Program Files (x86)/Tesseract-OCR/tesseract.exe
```

If Tesseract is not installed, digital PDFs can still be processed, but scanned PDFs and image OCR may return empty text or fallback values.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ClaimBlitz.git
cd ClaimBlitz
```

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a backend environment file:

```bash
cp .env.example .env
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

---

## Configuration

### Backend Environment Variables

Create `backend/.env`.

#### Optional Supabase Persistence

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_TABLE=claims
```

If Supabase variables are missing, claim processing still succeeds and persistence is skipped.

#### Optional OpenAI-Compatible LLM Risk Scoring

The active backend at `backend/app/main.py` uses the optional LLM risk settings below:

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=15
LLM_RISK_MODE=hybrid
LLM_MAX_ISSUES_FOR_LLM=3
LLM_ALLOWED_LABELS=MEDIUM
```

Supported `LLM_RISK_MODE` values:

- `hybrid` - rules first; call the LLM only for selected borderline claims.
- `off`, `false`, `0`, or `disabled` - never call the LLM.
- Any other enabled value attempts LLM scoring when configured.

#### Legacy Agent App LLM Variables

The older `backend/main.py` agent app uses Gemini/Ollama variables:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.1
LLM_TIMEOUT_SECONDS=45
USE_OLLAMA_ONLY=false
```

For the current frontend integration, run `uvicorn app.main:app`.

### Frontend Environment Variables

Create `frontend/.env` if the backend is not running at the default URL:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Default frontend API base URL:

```text
http://localhost:8000
```

---

## Running the Project

### Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Backend URLs:

- Health check: `http://localhost:8000/health`
- Swagger docs: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Frontend

Open a second terminal:

```bash
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

### Typical Demo Flow

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:5173`.
4. Click **Open Dashboard**.
5. Enable demo mode or upload a claim file.
6. Run the claim processing pipeline.
7. Review extracted claim data, risk score, risk reasons, and communication drafts.
8. Open the submission hub and launch an insurer portal clone.

---

## API Documentation

### Base URL

```text
http://localhost:8000
```

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Process Claim

```http
POST /process
Content-Type: multipart/form-data
```

Form field:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | file | Yes | Claim document. Supported extensions: PDF, PNG, JPG, JPEG |

Success response:

```json
{
  "claimData": {
    "patientName": "John D. Miller",
    "dob": "1985-03-14",
    "policyNumber": "882-ALT-9921",
    "diagnosisCode": "J18.9",
    "diagnosisDesc": "Pneumonia, unspecified organism",
    "cptCode": "99213",
    "provider": "SUMMIT HEALTH CLINIC",
    "totalBilled": 4250.0,
    "approvedAmount": 3612.5,
    "patientResponsibility": 637.5,
    "dateOfService": "2026-04-10"
  },
  "riskScore": 0.24,
  "riskLabel": "LOW",
  "recommendation": "APPROVE",
  "riskReasons": ["No major anomalies detected"],
  "extractionIssues": [],
  "extractionTextPreview": "Extracted document text preview...",
  "riskModel": {
    "engine": "rules",
    "modelName": "deterministic-rules-v1",
    "baseScore": 0.1,
    "maxIssuePenalty": 0.3,
    "issuePenaltyPerItem": 0.06,
    "thresholds": {
      "lowMax": 0.3,
      "mediumMax": 0.6,
      "highMax": 1.0
    },
    "contributions": []
  },
  "email": "Subject: Claim Review Update...",
  "whatsapp": "Claim Status Update..."
}
```

Error responses:

| Status | Cause |
| --- | --- |
| `400` | Missing filename or unsupported file type |
| `422` | Extraction failure or invalid multipart request |
| `500` | Unexpected backend error |

### Supported Output Fields

| Field | Description |
| --- | --- |
| `claimData` | Structured claim object |
| `riskScore` | Numeric risk score in `[0, 1]` |
| `riskLabel` | `LOW`, `MEDIUM`, or `HIGH` |
| `recommendation` | `APPROVE`, `REVIEW`, or `REJECT` |
| `riskReasons` | Human-readable risk and extraction reasons |
| `extractionIssues` | Missing, invalid, or derived-field warnings |
| `extractionTextPreview` | First 1200 characters of extracted text |
| `riskModel` | Engine metadata, thresholds, and contributions |
| `email` | Draft email for policyholder/claim communication |
| `whatsapp` | Draft short-form claim status update |

---

## Claim Processing Workflow

```text
User uploads document
        |
        v
File type validation
        |
        v
Text extraction
        |
        +-- Digital PDF text via pypdf
        +-- Scanned PDF OCR via PyMuPDF + Tesseract
        +-- Image OCR via Pillow + Tesseract
        |
        v
Regex and parser-based field extraction
        |
        v
Missing-field and fallback handling
        |
        v
Risk scoring
        |
        +-- Deterministic rules engine
        +-- Optional LLM scoring in configured modes
        |
        v
Communication draft generation
        |
        v
Optional Supabase persistence
        |
        v
JSON response to frontend
        |
        v
Frontend local-storage handoff to submission portal
```

---

## Risk Scoring Model

### Deterministic Rules Engine

The default scoring engine is deterministic and explainable.

Baseline:

```text
baseScore = 0.10
```

Signals that can increase risk:

- Invalid or missing total billed amount.
- Low approved-to-billed ratio.
- High claim amount.
- Invalid ICD-10 diagnosis code format.
- Invalid CPT procedure code format.
- Provider not present in the in-network reference list.
- Missing, invalid, or derived extraction fields.

Known in-network providers:

```text
SUMMIT HEALTH CLINIC
CITY CARE HOSPITAL
LIFELINE MEDICAL CENTER
```

### Risk Bands

| Score Range | Risk Label | Recommendation |
| --- | --- | --- |
| `0.00 - 0.30` | `LOW` | `APPROVE` |
| `0.31 - 0.60` | `MEDIUM` | `REVIEW` |
| `0.61 - 1.00` | `HIGH` | `REJECT` |

### LLM Risk Mode

When `LLM_API_KEY` is configured, the backend can call an OpenAI-compatible `/chat/completions` endpoint. The LLM is asked to return strict JSON with:

- `riskScore`
- `riskLabel`
- `recommendation`
- `reasons`
- `contributions`

If the LLM fails, times out, returns invalid JSON, or is not configured, the backend falls back to the deterministic rules result.

---

## Database and Persistence

Supabase persistence is optional. If configured, each processed claim is inserted into the configured table.

Suggested `claims` table columns:

| Column | Type |
| --- | --- |
| `id` | uuid primary key default `gen_random_uuid()` |
| `created_at` | timestamptz not null |
| `source_file` | text |
| `patient_name` | text |
| `policy_number` | text |
| `provider` | text |
| `diagnosis_code` | text |
| `cpt_code` | text |
| `total_billed` | numeric |
| `approved_amount` | numeric |
| `patient_responsibility` | numeric |
| `risk_score` | numeric |
| `risk_label` | text |
| `recommendation` | text |
| `email_draft` | text |
| `whatsapp_draft` | text |
| `claim_json` | jsonb |

Processing is intentionally non-blocking with respect to persistence. If Supabase is not configured or insertion fails, the API logs the issue and still returns the processed claim result.

---

## Frontend Experience

### Routes

| Route | Page | Purpose |
| --- | --- | --- |
| `/` | Landing page | Product intro and dashboard entry |
| `/dashboard` | Dashboard | Upload, process, inspect claim output |
| `/submission` | Submission hub | Select insurer portal clone |
| `/portal/:insurerId` | Portal clone | Auto-filled insurer form simulation |

### Browser Storage

The frontend stores the latest processed claim under:

```text
binaryblitz.latestClaim
```

This snapshot enables the submission hub and insurer portal clones to use extracted claim data without requiring a database lookup.

### Demo Payload

Demo mode uses a built-in low-risk claim with:

- Patient: `John D. Miller`
- Policy: `882-ALT-9921`
- Diagnosis: `J18.9`
- CPT: `99213`
- Provider: `SUMMIT HEALTH CLINIC`
- Recommendation: `APPROVE`

---

## Testing

### Backend Tests

```bash
cd backend
python -m pytest tests/ -v
```

Run a specific file:

```bash
python -m pytest tests/test_process_endpoint.py -v
```

Backend tests cover:

- Health endpoint.
- Missing file handling.
- Unsupported file type handling.
- Empty PDF fallback behavior.
- Valid PDF processing structure.
- Missing-field fallback values.
- Risk label and recommendation validity.
- Email and WhatsApp draft generation.
- Supabase persistence being optional.

### Frontend Tests

```bash
cd frontend
npm test
```

Run once:

```bash
npm test -- --run
```

Open Vitest UI:

```bash
npm run test:ui
```

Frontend tests cover:

- `useClaimAgent` initial state.
- Demo mode behavior.
- File upload handling.
- Processing state transitions.
- Agent status updates.
- Error handling.
- Reset behavior.
- Terminal log formatting.
- Risk score updates.

### Build Check

```bash
cd frontend
npm run build
```

---

## Troubleshooting

### Frontend Cannot Reach Backend

Check that the backend is running:

```text
http://localhost:8000/health
```

If the backend is on a different port, set:

```env
VITE_API_BASE_URL=http://localhost:YOUR_PORT
```

### OCR Returns Empty Text

- Confirm Tesseract OCR is installed.
- Confirm the uploaded file is readable.
- Try a digital PDF with embedded text.
- Check whether the document is rotated, blurry, password-protected, or image-only.

### Supabase Does Not Save Claims

- Confirm `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
- Confirm `SUPABASE_TABLE`.
- Confirm the table columns match the expected payload.
- Processing can still succeed even if persistence is skipped.

### LLM Is Not Being Used

- Confirm `LLM_API_KEY` is set.
- Confirm `LLM_RISK_MODE` is not disabled.
- In `hybrid` mode, only selected borderline claims are sent to the LLM.
- The deterministic rules engine remains the fallback.

### Unsupported File Type

Allowed extensions:

```text
.pdf
.png
.jpg
.jpeg
```

---

## Roadmap

### Completed

- FastAPI claim processing endpoint.
- PDF/image upload support.
- Digital PDF extraction.
- OCR fallback for scanned documents and images.
- Structured claim field extraction.
- Explainable deterministic risk scoring.
- Communication draft generation.
- React dashboard with agent-style progress.
- Local-storage handoff to submission flow.
- Insurer portal clone auto-fill simulation.
- Backend and frontend tests.

### In Progress / Planned

- Stronger OCR confidence scoring.
- More robust medical form parsing.
- Better high-risk sample library.
- Real insurer sandbox/API integration.
- Role-based review and approval workflow.
- Secure document storage.
- Multi-tenant organization support.
- Audit dashboard for claim decisions.
- Production deployment assets.

---

## Contributing

Contributions are welcome.

### Development Workflow

1. Fork the repository.
2. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

3. Make changes.
4. Add or update tests.
5. Run backend and frontend checks.
6. Submit a pull request.

### Code Standards

- Keep backend code typed and Pydantic-friendly.
- Keep API response shapes stable for the frontend hook.
- Prefer explainable rules for claim decisions.
- Keep optional integrations non-blocking.
- Use clear commit messages.

---

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

<div align="center">
  <p><strong>ClaimBlitz</strong></p>
  <p>Autonomous Medical Insurance Claim Processing</p>
  <p>Copyright (c) 2026 ClaimBlitz Team</p>
</div>
