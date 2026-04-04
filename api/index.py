from __future__ import annotations

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
