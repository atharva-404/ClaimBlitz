import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.models import ProcessResponse
from app.services.pipeline import ExtractionError, UnsupportedFileError, run_claim_pipeline
from app.services.supabase_store import SupabaseConfigError, persist_claim_result

logger = logging.getLogger(__name__)

# Load backend/.env automatically when app starts.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(
    title="Binary Blitz Claim Backend",
    version="0.1.0",
    description="FastAPI backend for autonomous medical claim processing.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process", response_model=ProcessResponse)
async def process_claim(file: UploadFile = File(...)) -> ProcessResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename in uploaded file.")

    # Read the stream to ensure upload validity and size checks can be added here.
    file_bytes = await file.read()

    try:
        result = run_claim_pipeline(file.filename, file_bytes)

        try:
            persist_claim_result(result, file.filename)
        except SupabaseConfigError:
            logger.warning("Supabase is not configured; skipping persistence.")
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to persist claim in Supabase: %s", exc)

        return result
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
