from __future__ import annotations

import asyncio
import json

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agents.comm_agent import run_comm_agent
from agents.doc_reader import run_doc_reader
from agents.form_filler import run_form_filler
from agents.validator import run_validator
from contracts import ProcessResponse
from services.llm_client import get_llm_client
from utils.pdf_parser import extract_text_from_pdf

load_dotenv()

app = FastAPI(title="Binary Blitz Claim Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\\n\\n"


def _validate_pdf_upload(file: UploadFile) -> None:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing file name")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "team": "Binary Blitz",
        "project": "Autonomous Medical Insurance Claim Agent",
        "llm": get_llm_client().provider_status(),
    }


@app.get("/health/providers")
def provider_health() -> dict:
    return get_llm_client().provider_status()


@app.post("/process", response_model=ProcessResponse)
async def process_claim(file: UploadFile = File(...)):
    _validate_pdf_upload(file)

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    pdf_text = extract_text_from_pdf(pdf_bytes)
    if not pdf_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    try:
        claim = await asyncio.to_thread(run_doc_reader, pdf_text)
        validation = await asyncio.to_thread(run_validator, claim)
        form_data = await asyncio.to_thread(run_form_filler, claim, validation)
        comms = await asyncio.to_thread(run_comm_agent, claim, validation)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc

    return {
        "claim": claim,
        "validation": validation,
        "form": form_data,
        "comms": comms,
    }


@app.post("/process-stream")
async def process_claim_stream(file: UploadFile = File(...)):
    _validate_pdf_upload(file)

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    pdf_text = extract_text_from_pdf(pdf_bytes)
    if not pdf_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    async def event_stream():
        try:
            yield _sse({"agent": 1, "name": "Doc Reader Agent", "status": "running"})
            claim = await asyncio.to_thread(run_doc_reader, pdf_text)
            yield _sse({"agent": 1, "name": "Doc Reader Agent", "status": "done", "result": claim})
            await asyncio.sleep(0.2)

            yield _sse({"agent": 2, "name": "Validator Agent", "status": "running"})
            validation = await asyncio.to_thread(run_validator, claim)
            yield _sse({"agent": 2, "name": "Validator Agent", "status": "done", "result": validation})
            await asyncio.sleep(0.2)

            yield _sse({"agent": 3, "name": "Form Filler Agent", "status": "running"})
            form_data = await asyncio.to_thread(run_form_filler, claim, validation)
            yield _sse({"agent": 3, "name": "Form Filler Agent", "status": "done", "result": form_data})
            await asyncio.sleep(0.2)

            yield _sse({"agent": 4, "name": "Comm Agent", "status": "running"})
            comms = await asyncio.to_thread(run_comm_agent, claim, validation)
            yield _sse({"agent": 4, "name": "Comm Agent", "status": "done", "result": comms})

            yield _sse(
                {
                    "agent": "complete",
                    "claim": claim,
                    "validation": validation,
                    "form": form_data,
                    "comms": comms,
                }
            )
        except Exception as exc:
            yield _sse({"agent": "error", "message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
