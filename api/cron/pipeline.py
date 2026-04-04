"""
Daily pipeline entrypoint for Vercel Cron.

Configured in vercel.json to receive GET requests from Vercel Cron (production only).
Secured with CRON_SECRET per https://vercel.com/docs/cron-jobs/manage-cron-jobs

Executes pipeline_prod.ipynb with nbclient (same code cells as Jupyter). The notebook
expects shop.db in the working directory (copied into web/pipeline/ at build time when
the file exists in the repo root — see scripts/sync-pipeline-assets.mjs).

Hobby tier functions max out at 60s; this notebook usually needs longer. On Pro, raise
maxDuration for api/cron/pipeline.py in vercel.json (for example 300 seconds).
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import nbformat
from nbclient import NotebookClient

app = FastAPI()


def _web_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _authorize(request: Request) -> None:
    secret = os.environ.get("CRON_SECRET")
    if not secret:
        return
    auth = request.headers.get("authorization")
    if auth != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _execute_notebook() -> dict:
    os.environ.setdefault("MPLBACKEND", "Agg")
    for k, v in (
        ("OMP_NUM_THREADS", "1"),
        ("OPENBLAS_NUM_THREADS", "1"),
        ("MKL_NUM_THREADS", "1"),
        ("LOKY_MAX_CPU_COUNT", "1"),
    ):
        os.environ.setdefault(k, v)

    web = _web_root()
    rel = os.environ.get("PIPELINE_NOTEBOOK", "pipeline/pipeline_prod.ipynb")
    nb_path = (web / rel).resolve()
    cwd = Path(os.environ.get("PIPELINE_CWD", str(nb_path.parent))).resolve()

    if not nb_path.is_file():
        return {
            "ok": False,
            "error": f"Notebook not found: {nb_path}",
            "hint": "Ensure pipeline_prod.ipynb is copied into web/pipeline/ during build "
            "(sync-pipeline-assets.mjs) or set PIPELINE_NOTEBOOK.",
        }

    try:
        with open(nb_path, encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
    except OSError as e:
        return {"ok": False, "error": f"Failed to read notebook: {e}"}

    timeout = int(os.environ.get("PIPELINE_TIMEOUT_SECONDS", "600"))
    client = NotebookClient(
        nb,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(cwd)}},
    )
    try:
        client.execute()
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    return {
        "ok": True,
        "notebook": str(nb_path),
        "cwd": str(cwd),
        "cells": len(nb.cells),
    }


@app.get("/")
def run_pipeline(request: Request):
    _authorize(request)
    result = _execute_notebook()
    status = 200 if result.get("ok") else 500
    return JSONResponse(content=result, status_code=status)
