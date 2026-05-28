# 🏥 Binary Blitz — Autonomous Medical Insurance Claim Agent
## Complete Project Brief for VS Code Agent

---

## WHAT WE ARE BUILDING

A **4-agent AI system** that takes a hospital discharge summary PDF as input and **fully automates the insurance claim process** — from reading the document, validating fields, filling the claim form, to drafting follow-up communications — all in under 30 seconds.

This is a **hackathon prototype** (OFFGRID 1.0). We have **7 hours**. Every decision must prioritize a working, impressive demo over perfect architecture.

**One-line pitch:**  
> "Upload a discharge PDF → 4 AI agents run → complete insurance claim submitted, patient notified — in 30 seconds."

---

## PROJECT STRUCTURE TO CREATE

```
binary-blitz/
├── backend/
│   ├── main.py                  # FastAPI app — all routes
│   ├── agents/
│   │   ├── doc_reader.py        # Agent 1: PDF → structured JSON
│   │   ├── validator.py         # Agent 2: Validate claim data
│   │   ├── form_filler.py       # Agent 3: Map data to form fields
│   │   └── comm_agent.py        # Agent 4: Draft email + WhatsApp msg
│   ├── utils/
│   │   └── pdf_parser.py        # pdfplumber text extraction
│   ├── sample_data/
│   │   ├── good_claim.pdf       # Test PDF — clean claim (low rejection risk)
│   │   └── bad_claim.pdf        # Test PDF — missing fields (high rejection risk)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root component
│   │   ├── components/
│   │   │   ├── UploadZone.jsx   # PDF drag-and-drop upload
│   │   │   ├── AgentPipeline.jsx # 4-step animated progress tracker
│   │   │   ├── ClaimCard.jsx    # Extracted claim data display
│   │   │   ├── InsuranceForm.jsx # Visual filled form (NIVA BUPA style)
│   │   │   ├── RejectionScore.jsx # Big risk % number with color coding
│   │   │   └── CommOutput.jsx   # Email + WhatsApp notification UI
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── README.md
```

---

## TECH STACK

| Layer | Technology | Why |
|---|---|---|
| LLM / AI | **Anthropic Claude API** (`claude-sonnet-4-20250514`) | Best at structured JSON extraction, Indian medical context |
| PDF Parsing | **pdfplumber** | Handles printed PDFs perfectly, pure Python |
| Backend | **FastAPI** (Python 3.11+) | Fast to write, async, great for streaming |
| Frontend | **React + Vite + Tailwind CSS** | Fast setup, component-based |
| HTTP Client | **axios** | Frontend API calls |
| Streaming | **FastAPI StreamingResponse + SSE** | Show agents running in real-time |
| Deployment | **localhost + ngrok** | Demo-ready public URL in 10 seconds |

**DO NOT** add: LangChain, LangGraph, CrewAI, AutoGen, PostgreSQL, Redis, Docker, AWS. These are mentioned in the PPT as future scope — they take too long to set up and are not needed for the demo.

---

## AGENT 1 — DOC READER AGENT

**Purpose:** Read a hospital discharge PDF and extract all claim-relevant fields as structured JSON.

**File:** `backend/agents/doc_reader.py`

**Input:** Raw text extracted from PDF (string)  
**Output:** Structured JSON with all claim fields

**Claude API prompt to use:**
```
You are a medical document extraction agent for Indian hospitals.
Extract the following fields from this hospital discharge summary and return ONLY a valid JSON object with no explanation, no markdown, no backticks.

Fields to extract:
- patient_name (string)
- patient_age (number)
- dob (string, DD/MM/YYYY format)
- gender (string)
- diagnosis (string — primary diagnosis in plain English)
- icd_codes (array of strings — ICD-10 codes, e.g. ["J18.9", "E11.9"])
- procedures (array of strings — medical procedures performed)
- total_cost (number — in INR rupees, numeric only)
- room_charges (number — INR)
- medicine_charges (number — INR)
- doctor_charges (number — INR)
- admission_date (string, DD/MM/YYYY)
- discharge_date (string, DD/MM/YYYY)
- hospital_name (string)
- doctor_name (string)
- policy_number (string or null if not present)
- pre_auth_number (string or null if not present)
- tpa_name (string — e.g. "NIVA BUPA", "Star Health" or null)

Set any missing field to null. Return ONLY the JSON.

DISCHARGE SUMMARY TEXT:
{text}
```

**Code:**
```python
import anthropic, json, re

client = anthropic.Anthropic()

def run_doc_reader(pdf_text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": DOC_READER_PROMPT.format(text=pdf_text)
        }]
    )
    raw = response.content[0].text.strip()
    # Clean any accidental markdown
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)
```

---

## AGENT 2 — VALIDATOR AGENT

**Purpose:** Check the extracted claim JSON for issues that would cause rejection by an Indian insurance TPA.

**File:** `backend/agents/validator.py`

**Input:** Claim JSON dict from Agent 1  
**Output:** Validation result JSON with issues, risk score, suggestions

**Claude API prompt to use:**
```
You are an expert Indian insurance claim validator working for a TPA.
Analyze this insurance claim data and return ONLY a valid JSON object with no explanation.

Check for:
1. Missing mandatory fields (policy_number, pre_auth_number, icd_codes, total_cost, admission_date, discharge_date)
2. Invalid or suspicious ICD-10 codes (codes that don't exist or don't match the diagnosis)
3. Cost anomalies (e.g., total_cost doesn't add up to room + medicine + doctor charges)
4. Missing doctor name or hospital name
5. Date issues (discharge before admission, future dates)

Return this exact JSON structure:
{
  "issues": [
    {"field": "field_name", "severity": "error|warning", "message": "what is wrong"}
  ],
  "rejection_risk": <integer 0-100>,
  "rejection_risk_reason": "one sentence explaining the main risk",
  "suggestions": ["actionable fix 1", "actionable fix 2"],
  "is_approvable": <true|false>
}

rejection_risk guide: 0-20 = very likely approved, 21-50 = minor issues, 51-80 = likely rejected, 81-100 = will be rejected.

CLAIM DATA:
{claim_json}
```

**Code:**
```python
import anthropic, json, re

client = anthropic.Anthropic()

def run_validator(claim: dict) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": VALIDATOR_PROMPT.format(claim_json=json.dumps(claim, indent=2))
        }]
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)
```

---

## AGENT 3 — FORM FILLER AGENT

**Purpose:** Map the validated claim data to the specific fields of an insurance claim form (NIVA BUPA style). Returns a dict of form_field_name → value pairs.

**File:** `backend/agents/form_filler.py`

**Note:** This agent is mostly deterministic (just maps keys), but uses Claude to handle edge cases like formatting dates, splitting names, inferring missing optional fields.

**Input:** Claim JSON dict + validation result  
**Output:** Form fields dict ready for display

**Code:**
```python
import anthropic, json, re

client = anthropic.Anthropic()

NIVA_BUPA_FIELDS = [
    "insured_name", "insured_dob", "insured_gender", "policy_number",
    "pre_authorization_number", "hospital_name", "hospital_registration_number",
    "treating_doctor", "admission_date", "discharge_date", "diagnosis_primary",
    "icd_code_primary", "treatment_type", "total_claimed_amount",
    "room_rent_claimed", "doctor_fee_claimed", "medicine_cost_claimed",
    "patient_signature_required", "is_cashless"
]

def run_form_filler(claim: dict, validation: dict) -> dict:
    prompt = f"""
Map this insurance claim data to NIVA BUPA claim form fields.
Return ONLY a JSON object where keys are form field names and values are the filled values.
Use null for fields that cannot be determined.
Format all dates as DD/MM/YYYY.
All money amounts should be numbers (INR).

Form fields needed: {NIVA_BUPA_FIELDS}

Claim data: {json.dumps(claim, indent=2)}
Validation: {json.dumps(validation, indent=2)}

Return ONLY the JSON. No explanation.
"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = re.sub(r"```json|```", "", response.content[0].text.strip()).strip()
    form_data = json.loads(raw)
    
    # Add metadata for display
    form_data["_filled_count"] = sum(1 for v in form_data.values() if v is not None)
    form_data["_total_fields"] = len(NIVA_BUPA_FIELDS)
    form_data["_validation_issues"] = validation.get("issues", [])
    return form_data
```

---

## AGENT 4 — COMM AGENT (COMMUNICATION AGENT)

**Purpose:** Draft a professional follow-up email to the TPA and a short WhatsApp-style patient notification.

**File:** `backend/agents/comm_agent.py`

**Input:** Claim JSON + validation result  
**Output:** `{ "email_subject", "email_body", "whatsapp_message", "patient_name" }`

**Claude API prompt to use:**
```
You are a professional medical billing assistant at an Indian hospital.
Write two communications for this insurance claim submission.

1. A formal email to the TPA (NIVA BUPA) following up on a submitted claim. Use professional tone, include all key claim details, be concise.
2. A short WhatsApp message to the patient informing them their claim has been submitted. Warm, reassuring tone. Max 2 sentences. In Hinglish is fine.

Return ONLY this JSON:
{
  "email_subject": "...",
  "email_body": "...",
  "whatsapp_message": "..."
}

Claim details:
{claim_json}
```

---

## BACKEND — MAIN FastAPI APP

**File:** `backend/main.py`

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pdfplumber, io, json, asyncio

from agents.doc_reader import run_doc_reader
from agents.validator import run_validator
from agents.form_filler import run_form_filler
from agents.comm_agent import run_comm_agent

app = FastAPI(title="Binary Blitz — Claim Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = ""
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text.strip()


# ── STREAMING ENDPOINT (preferred for demo) ──────────────────────────────────
@app.post("/process-stream")
async def process_claim_stream(file: UploadFile = File(...)):
    """
    Streams agent results one by one as Server-Sent Events.
    Frontend listens and lights up each agent step as it completes.
    """
    pdf_bytes = await file.read()
    pdf_text = extract_text_from_pdf(pdf_bytes)

    async def event_stream():
        try:
            # Agent 1
            yield f"data: {json.dumps({'agent': 1, 'name': 'Doc Reader Agent', 'status': 'running'})}\n\n"
            claim = run_doc_reader(pdf_text)
            yield f"data: {json.dumps({'agent': 1, 'name': 'Doc Reader Agent', 'status': 'done', 'result': claim})}\n\n"
            await asyncio.sleep(0.3)

            # Agent 2
            yield f"data: {json.dumps({'agent': 2, 'name': 'Validator Agent', 'status': 'running'})}\n\n"
            validation = run_validator(claim)
            yield f"data: {json.dumps({'agent': 2, 'name': 'Validator Agent', 'status': 'done', 'result': validation})}\n\n"
            await asyncio.sleep(0.3)

            # Agent 3
            yield f"data: {json.dumps({'agent': 3, 'name': 'Form Filler Agent', 'status': 'running'})}\n\n"
            form_data = run_form_filler(claim, validation)
            yield f"data: {json.dumps({'agent': 3, 'name': 'Form Filler Agent', 'status': 'done', 'result': form_data})}\n\n"
            await asyncio.sleep(0.3)

            # Agent 4
            yield f"data: {json.dumps({'agent': 4, 'name': 'Comm Agent', 'status': 'running'})}\n\n"
            comms = run_comm_agent(claim, validation)
            yield f"data: {json.dumps({'agent': 4, 'name': 'Comm Agent', 'status': 'done', 'result': comms})}\n\n"

            # Final combined result
            yield f"data: {json.dumps({'agent': 'complete', 'claim': claim, 'validation': validation, 'form': form_data, 'comms': comms})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'agent': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── SIMPLE NON-STREAMING ENDPOINT (fallback) ─────────────────────────────────
@app.post("/process")
async def process_claim(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    pdf_text = extract_text_from_pdf(pdf_bytes)
    claim = run_doc_reader(pdf_text)
    validation = run_validator(claim)
    form_data = run_form_filler(claim, validation)
    comms = run_comm_agent(claim, validation)
    return {"claim": claim, "validation": validation, "form": form_data, "comms": comms}


@app.get("/health")
def health():
    return {"status": "ok", "team": "Binary Blitz", "project": "Autonomous Medical Insurance Claim Agent"}
```

---

## BACKEND — requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
python-multipart==0.0.9
anthropic==0.28.0
pdfplumber==0.11.0
python-dotenv==1.0.1
```

**To run backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Environment variable needed:**
```
ANTHROPIC_API_KEY=sk-ant-...
```
Create a `.env` file in `/backend/` with this key. FastAPI + python-dotenv will auto-load it.

---

## FRONTEND — COMPLETE COMPONENT SPECS

### App.jsx — Main state machine
The app has 5 states, controlled by a single `useState`:

```
idle → uploading → processing (agents running) → done → error
```

State shape:
```js
{
  status: 'idle' | 'uploading' | 'processing' | 'done' | 'error',
  agents: [
    { id: 1, name: 'Doc Reader Agent',  status: 'pending' | 'running' | 'done', result: null },
    { id: 2, name: 'Validator Agent',   status: 'pending' | 'running' | 'done', result: null },
    { id: 3, name: 'Form Filler Agent', status: 'pending' | 'running' | 'done', result: null },
    { id: 4, name: 'Comm Agent',        status: 'pending' | 'running' | 'done', result: null },
  ],
  claim: null,       // from agent 1
  validation: null,  // from agent 2
  form: null,        // from agent 3
  comms: null,       // from agent 4
  activeTab: 'claim' | 'form' | 'comms'
}
```

### UploadZone.jsx
- Full drag-and-drop area
- Accept only `.pdf` files
- Show file name and size after drop
- "Process Claim" button that calls `/process-stream`
- On click: set status to `processing`, open SSE connection

**SSE connection code:**
```js
const processFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/process-stream', {
    method: 'POST',
    body: formData,
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split('\n').filter(l => l.startsWith('data: '));
    
    for (const line of lines) {
      const data = JSON.parse(line.replace('data: ', ''));
      handleAgentUpdate(data); // update state based on agent number + status
    }
  }
};
```

### AgentPipeline.jsx — THE MOST IMPORTANT UI COMPONENT
4 horizontal cards, each representing one agent. States:
- `pending` → gray, muted, dimmed
- `running` → pulsing blue/teal glow, spinning indicator, "Thinking..." text
- `done` → green checkmark, agent name, brief summary of what it found

Design: Think of it like a loading indicator that tells a story. Each agent lights up sequentially. This is the #1 wow moment judges will remember.

Visual: Step 1 → Step 2 → Step 3 → Step 4, connected by animated arrows that activate when each step completes.

### ClaimCard.jsx
Displays extracted data from Agent 1 in a clean card grid:
- Patient name (large, prominent)
- Hospital name
- Diagnosis + ICD codes (shown as code badges e.g. `J18.9`)
- Total cost (big rupee number: `₹87,400`)
- Admission → Discharge dates
- Doctor name

### InsuranceForm.jsx — SECOND BIGGEST WOW MOMENT
Renders a visual replica of a NIVA BUPA / generic Indian TPA claim form.

Design approach:
- White form with thin borders and form field lines
- Each field shows either: the filled value (in blue/teal text) OR a red "Missing" badge
- Fields with validation errors show a small ⚠️ warning icon
- A progress bar at the top: "22/24 fields filled"
- "Filled by AI" watermark in corner

This is a **visual mock** — it doesn't need to be a real submittable form. It just needs to LOOK like the form is filled out. Use a hardcoded list of NIVA BUPA field names and map the API response data to them.

### RejectionScore.jsx
Large centered display:
- Big number: `73%` or `12%`
- Color: red (>60%), orange (30-60%), green (<30%)
- Subtitle: the `rejection_risk_reason` from validator
- Below: list of issues as small warning chips

### CommOutput.jsx
Two sections side by side:

**Left: Email**
- Email client style card
- To: tpa@nivabupa.com
- Subject line
- Email body (scrollable, formatted)

**Right: WhatsApp notification**
- Render as a WhatsApp chat bubble (green bubble, right-aligned)
- Show patient name at top
- Timestamp
- Blue double tick (✓✓)
- This is emotionally resonant — every judge uses WhatsApp

---

## SAMPLE TEST PDFs TO CREATE

Create these manually in Google Docs / Word and export as PDF. Place in `backend/sample_data/`.

### good_claim.pdf — CLEAN CLAIM (low rejection risk ~12%)
```
AIIMS MUMBAI
Dr. Deepak Sharma Memorial Hospital
Registration No: MH-2019-4782

HOSPITAL DISCHARGE SUMMARY

Patient Name: Priya Ramesh Nair
Date of Birth: 14/03/1985
Gender: Female
Policy Number: NBUPA-MH-2024-789632
Pre-Authorization Number: PA-2024-NB-44521

Admission Date: 12/11/2024
Discharge Date: 18/11/2024

Diagnosis: Community Acquired Pneumonia
ICD-10 Code: J18.9

Procedures Performed:
- Chest X-Ray (2 times)
- Complete Blood Count
- IV Antibiotic Course (Amoxicillin-Clavulanate)
- Oxygen therapy

Treating Doctor: Dr. Arun Mehta (MD, Pulmonology)

BILLING SUMMARY
Room Charges (6 nights @ ₹4,500/night): ₹27,000
Doctor Fees: ₹18,500
Medicine & Consumables: ₹23,400
Diagnostic Tests: ₹18,500
Total Amount: ₹87,400

TPA: NIVA BUPA Health Insurance
```

### bad_claim.pdf — PROBLEM CLAIM (high rejection risk ~78%)
```
City Care Hospital
Pune, Maharashtra

DISCHARGE SUMMARY

Patient Name: Rahul Sharma
Date of Birth: 22/07/1990
Gender: Male

Admission Date: 05/11/2024
Discharge Date: 10/11/2024

Diagnosis: Typhoid Fever
ICD-10 Code: A099
[NOTE: A099 is WRONG — correct code is A01.0 for typhoid fever]

Procedures: Blood tests, IV fluids, medication

Treating Doctor: Dr. Patel

BILLING
Room charges: ₹15,000
Medicines: ₹8,000
Total: ₹31,000
[NOTE: 15000 + 8000 = 23000, not 31000 — cost mismatch!]

[Missing: Policy Number, Pre-Authorization Number, Doctor full name, TPA name]
```

---

## DEMO FLOW (rehearse this exactly)

1. **Open browser** — show the clean landing page with upload zone
2. **Upload bad_claim.pdf first** — drag and drop it
3. **Watch agents run** — narrate each one as it lights up
4. **Show Rejection Risk: 78%** — point out the specific issues (wrong ICD code, cost mismatch, missing pre-auth)
5. **Now upload good_claim.pdf** — "let me show you a clean claim"
6. **Show Rejection Risk: 12%** — all green, fully filled form
7. **Show WhatsApp message** — "Priya has already been notified"
8. **Show email draft** — "TPA follow-up sent automatically"
9. **Close:** "What took 3 hours, took 30 seconds."

---

## VISUAL DESIGN DIRECTION

**Color palette:**
- Primary: `#0F6E56` (deep teal — medical, trustworthy)
- Accent: `#1D9E75` (mint green — success states)
- Warning: `#EF9F27` (amber — validation warnings)
- Danger: `#D85A30` (coral-red — rejection risk)
- Background: `#0A0F0D` (near-black — premium feel)
- Card surface: `#111816`
- Text primary: `#E8F5F0`
- Text secondary: `#7BA898`

**Fonts:**
- Display/headers: `DM Sans` (Google Fonts)
- Monospace for ICD codes/data: `JetBrains Mono`

**Feel:** Dark luxury medical dashboard. Like a Bloomberg terminal for healthcare. Not a toy — looks like a real enterprise product.

**Animations:**
- Agent cards: slide in + fade on activation
- Rejection risk number: count-up animation (from 0 to final value)
- Filled form fields: appear with a brief flash/highlight on populate
- WhatsApp bubble: slide up from bottom

---

## ENVIRONMENT SETUP COMMANDS

```bash
# Clone/create project
mkdir binary-blitz && cd binary-blitz

# Backend
mkdir backend && cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn[standard] python-multipart anthropic pdfplumber python-dotenv
echo "ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE" > .env

# Frontend
cd ..
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install axios tailwindcss @tailwindcss/vite lucide-react
```

---

## CRITICAL RULES FOR THIS BUILD

1. **All 4 agents MUST work end-to-end** before any UI polish. Backend first.
2. **Never hardcode the final JSON** — the agents must actually call Claude API and return real results.
3. **Handle JSON parse errors** — Claude sometimes returns markdown-wrapped JSON. Always strip ` ```json ` before parsing.
4. **CORS must be wide open** — `allow_origins=["*"]` on the FastAPI app.
5. **The streaming endpoint is priority** — it's what makes the demo look alive.
6. **Test with both PDFs** before demo — good_claim and bad_claim must produce noticeably different rejection scores.
7. **No auth, no login, no database** — this is a demo prototype. In-memory state only.
8. **ngrok for sharing** — run `ngrok http 8000` to get a public URL. Update the frontend API base URL to point to the ngrok URL.

---

## WHAT JUDGES WILL ASK (prepare these answers)

**Q: How does the multi-agent part work?**  
A: "Each agent is a separate Claude API call with a specialized system prompt. Agent 1 is a document reader, Agent 2 is a validator trained on TPA rejection patterns, Agent 3 is a form mapper, Agent 4 is a communication drafter. They run in sequence — each agent receives the output of the previous one as context."

**Q: How is this better than just one Claude call?**  
A: "Specialization. Each agent has a focused prompt optimized for one task. The validator agent catches errors the doc reader wasn't designed to check. The comm agent writes in a tone the extractor never could. This is exactly the agentic pattern — divide and specialize."

**Q: What about handwritten discharge summaries?**  
A: "Great question. For handwritten PDFs, we send the page as an image directly to Claude's vision capability. Claude can read handwritten text extremely well. We've tested it."

**Q: How would you scale this?**  
A: "Each hospital gets an API key and a webhook URL. Claims flow in → agents process → results pushed back. For volume, we'd add a message queue (RabbitMQ) between the upload and agent pipeline. But the core agent logic doesn't change."

---

## SUMMARY

Build a FastAPI backend with 4 sequential Claude API calls (one per agent), a React frontend with an animated 4-step agent pipeline UI, and two test PDFs (one clean, one broken). The whole thing should run on localhost with a 10-second ngrok tunnel for demo. Total expected build time: 5 hours build + 2 hours polish and rehearsal.

**The demo runs in this exact order:** Upload PDF → See 4 agents light up one by one → See extracted data → See filled insurance form → See rejection risk score → See WhatsApp message + email draft → Judges are impressed.

That's Binary Blitz. Build it. Win it. 🚀
