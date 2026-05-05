# 🏥 ClaimBlitz (formerly Binary Blitz)

**ClaimBlitz** is an Autonomous Medical Insurance Claim Agent. It's a 4-agent AI system that takes a hospital discharge summary PDF as input and fully automates the insurance claim process — from reading the document, validating fields, and filling the claim form, to drafting follow-up communications, all in under 30 seconds.

## 🚀 Features

- **Agent 1 (Doc Reader)**: Extracts claim-relevant fields from a discharge PDF into structured JSON.
- **Agent 2 (Validator)**: Checks extracted data for issues that would cause rejection by an Indian insurance TPA.
- **Agent 3 (Form Filler)**: Maps validated claim data to specific fields of an insurance claim form (NIVA BUPA style).
- **Agent 4 (Comm Agent)**: Drafts a professional follow-up email to the TPA and a WhatsApp notification for the patient.

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Anthropic Claude API (`claude-3.5-sonnet` / Gemini as primary LLM), `pdfplumber` for PDF parsing.
- **Frontend**: React, Vite, Tailwind CSS, Axios.
- **Architecture**: Streaming SSE (Server-Sent Events) to show agents running in real-time.

## 📂 Project Structure

```
ClaimBlitz/
├── backend/                  # FastAPI Backend API
│   ├── agents/               # 4 specialized AI Agents
│   ├── app/                  # Main FastAPI Application Setup
│   ├── services/             # LLM and Pipeline services
│   ├── test_data/            # Sample PDFs for testing
│   ├── utils/                # PDF Parsing, JSON cleaning tools
│   ├── main.py               # Application entry point
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React Vite Frontend
│   ├── src/                  # React Components, Hooks, Pages
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite config
└── test_claim.pdf            # Sample test file
```

## ⚙️ How to Run Locally

### 1. Setup Backend
```bash
cd backend
python -m venv venv
# Activate virtual environment
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt

# Create .env file from the example
cp .env.example .env
# Make sure to fill in your API keys in the .env file

# Run the server
uvicorn main:app --reload --port 8000
```

### 2. Setup Frontend
```bash
cd frontend
npm install

# Start the dev server
npm run dev
```

## 🧪 Testing

You can use the provided sample PDFs in `backend/test_data/` to test the application's capabilities. Drag and drop the PDFs onto the UI to see the multi-agent pipeline process the document in real-time.

---
*Built for the Hackathon.*
