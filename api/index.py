from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load before importing app modules so DATABASE_URL is set for inference/cron.
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / "web" / ".env")
load_dotenv(_root / ".env", override=False)

from fastapi import FastAPI, Request

from api.cron.pipeline import run_pipeline
from api.inference.run import health_check, run_batch

app = FastAPI()


@app.get("/")
def root_health():
    return {"ok": True, "message": "Backend API is healthy."}


@app.get("/api/inference/run")
def inference_health():
    return health_check()


@app.post("/api/inference/run")
def inference_run(request: Request):
    return run_batch(request)


@app.get("/api/cron/pipeline")
def pipeline_run(request: Request):
    return run_pipeline(request)
