"""
Late-delivery batch inference for unfulfilled orders.

Reads training labels from orders + shipments, fits a small sklearn pipeline,
upserts ``order_predictions``. Invoked over HTTP (Next.js server action uses fetch),
not via shelling out to python on the Node runtime.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

app = FastAPI()

TRAIN_SQL = """
SELECT o.order_id, o.num_items, o.total_value, o.avg_weight,
       s.carrier, s.shipping_method, s.distance_band, s.promised_days,
       COALESCE(s.actual_days, -1.0) AS actual_days_feat,
       s.late_delivery::int AS y
FROM orders o
INNER JOIN shipments s ON s.order_id = o.order_id
WHERE s.late_delivery IS NOT NULL
"""

SCORE_SQL = """
SELECT o.order_id, o.num_items, o.total_value, o.avg_weight,
       s.carrier, s.shipping_method, s.distance_band, s.promised_days,
       COALESCE(s.actual_days, -1.0) AS actual_days_feat
FROM orders o
INNER JOIN shipments s ON s.order_id = o.order_id
WHERE o.fulfilled = 0
"""

NUMERIC = [
    "num_items",
    "total_value",
    "avg_weight",
    "promised_days",
    "actual_days_feat",
]
CATEGORICAL = ["carrier", "shipping_method", "distance_band"]


def _authorize(request: Request) -> None:
    secret = os.environ.get("INFERENCE_API_SECRET")
    auth = request.headers.get("authorization")
    if os.environ.get("VERCEL"):
        if not secret:
            raise HTTPException(
                status_code=500, detail="INFERENCE_API_SECRET is not configured"
            )
        if auth != f"Bearer {secret}":
            raise HTTPException(status_code=401, detail="Unauthorized")
        return
    if secret and auth != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _decision_threshold() -> float:
    raw_threshold = os.environ.get("LATE_DELIVERY_DECISION_THRESHOLD", "0.5")
    try:
        threshold = float(raw_threshold)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="LATE_DELIVERY_DECISION_THRESHOLD must be a number between 0 and 1",
        ) from exc

    if threshold < 0 or threshold > 1:
        raise HTTPException(
            status_code=500,
            detail="LATE_DELIVERY_DECISION_THRESHOLD must be between 0 and 1",
        )

    return threshold


def _read_df(conn: psycopg.Connection, sql: str) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [c.name for c in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)


def _build_model(train_df: pd.DataFrame) -> Pipeline | None:
    if train_df.empty or train_df["y"].nunique() < 2:
        return None
    X = train_df[NUMERIC + CATEGORICAL]
    y = train_df["y"].astype(int)
    pre = ColumnTransformer(
        transformers=[
            (
                "num",
                SimpleImputer(strategy="median"),
                NUMERIC,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "oh",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                CATEGORICAL,
            ),
        ]
    )
    clf = Pipeline(
        steps=[
            ("pre", pre),
            (
                "lr",
                LogisticRegression(
                    max_iter=200, class_weight="balanced", random_state=42
                ),
            ),
        ]
    )
    clf.fit(X, y)
    return clf


def _run_inference() -> dict:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return {"ok": False, "error": "DATABASE_URL is not set"}

    threshold = _decision_threshold()

    with psycopg.connect(database_url) as conn:
        train_df = _read_df(conn, TRAIN_SQL)
        score_df = _read_df(conn, SCORE_SQL)

        if score_df.empty:
            return {
                "ok": True,
                "updated": 0,
                "message": "No unfulfilled orders with shipment rows to score.",
            }

        model = _build_model(train_df)
        X_score = score_df[NUMERIC + CATEGORICAL]

        if model is None:
            baseline = float(train_df["y"].mean()) if not train_df.empty else 0.25
            baseline = min(max(baseline, 0.05), 0.95)
            proba = np.full(len(score_df), baseline)
        else:
            proba = model.predict_proba(X_score)[:, 1]

        pred = (proba >= threshold).astype(int)
        ts = datetime.now(timezone.utc)

        rows = list(
            zip(
                score_df["order_id"].astype(int),
                proba.astype(float),
                pred.astype(int),
                strict=True,
            )
        )

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO order_predictions (
                  order_id, late_delivery_probability, predicted_late_delivery, prediction_timestamp
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (order_id) DO UPDATE SET
                  late_delivery_probability = EXCLUDED.late_delivery_probability,
                  predicted_late_delivery = EXCLUDED.predicted_late_delivery,
                  prediction_timestamp = EXCLUDED.prediction_timestamp
                """,
                [(oid, float(p), int(pr), ts) for oid, p, pr in rows],
            )
        conn.commit()

    return {
        "ok": True,
        "updated": len(rows),
        "message": f"Upserted predictions for {len(rows)} unfulfilled order(s).",
        "training_rows": len(train_df),
        "decision_threshold": threshold,
    }


@app.get("/")
def health_check():
    return {
        "ok": True,
        "message": "Inference endpoint is healthy.",
        "decision_threshold": _decision_threshold(),
    }


@app.post("/")
def run_batch(request: Request):
    _authorize(request)
    try:
        result = _run_inference()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )
    status = 200 if result.get("ok") else 500
    return JSONResponse(content=result, status_code=status)
