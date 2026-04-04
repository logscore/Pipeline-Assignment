from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
import os

import psycopg
from psycopg.rows import dict_row

from api._inference import (
    DEFAULT_DECISION_THRESHOLD,
    OrderPrediction,
    PendingOrder,
    score_pending_order,
    summarize_predictions,
)

MODEL_NAME = "late-delivery-baseline-v1"

FETCH_PENDING_ORDERS_SQL = """
WITH overall_stats AS (
    SELECT COALESCE(AVG(s.late_delivery::float), 0.18) AS overall_late_rate
    FROM shipments s
    WHERE s.late_delivery IS NOT NULL
), customer_stats AS (
    SELECT
        o.customer_id,
        COUNT(*) FILTER (WHERE s.late_delivery IS NOT NULL) AS prior_shipments,
        COALESCE(SUM(CASE WHEN s.late_delivery = 1 THEN 1 ELSE 0 END), 0) AS prior_late_shipments,
        AVG(s.promised_days) AS avg_promised_days,
        AVG(s.actual_days) AS avg_actual_days,
        AVG(s.actual_days - s.promised_days) AS avg_delivery_gap
    FROM orders o
    INNER JOIN shipments s ON s.order_id = o.order_id
    WHERE o.fulfilled = 1
    GROUP BY o.customer_id
)
SELECT
    o.order_id,
    EXTRACT(EPOCH FROM (NOW() - o.order_timestamp)) / 3600.0 AS order_age_hours,
    COALESCE(o.num_items, 0) AS num_items,
    COALESCE(o.total_value, 0) AS total_value,
    COALESCE(o.avg_weight, 0) AS avg_weight,
    COALESCE(cs.prior_shipments, 0) AS prior_shipments,
    COALESCE(cs.prior_late_shipments, 0) AS prior_late_shipments,
    COALESCE(cs.avg_promised_days, 0) AS avg_promised_days,
    COALESCE(cs.avg_actual_days, 0) AS avg_actual_days,
    COALESCE(cs.avg_delivery_gap, 0) AS avg_delivery_gap,
    os.overall_late_rate AS overall_late_rate
FROM orders o
CROSS JOIN overall_stats os
LEFT JOIN customer_stats cs ON cs.customer_id = o.customer_id
WHERE o.fulfilled = 0
"""

UPSERT_PREDICTIONS_SQL = """
INSERT INTO order_predictions (
    order_id,
    late_delivery_probability,
    predicted_late_delivery,
    prediction_timestamp
)
VALUES (%s, %s, %s, NOW())
ON CONFLICT (order_id) DO UPDATE SET
    late_delivery_probability = EXCLUDED.late_delivery_probability,
    predicted_late_delivery = EXCLUDED.predicted_late_delivery,
    prediction_timestamp = EXCLUDED.prediction_timestamp
"""


class BadRequestError(Exception):
    pass


class ConfigurationError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ConfigurationError("DATABASE_URL is required.")
    return database_url


def get_decision_threshold() -> float:
    raw_threshold = os.getenv("LATE_DELIVERY_DECISION_THRESHOLD")
    if not raw_threshold:
        return DEFAULT_DECISION_THRESHOLD

    try:
        threshold = float(raw_threshold)
    except ValueError as exc:
        raise ConfigurationError(
            "LATE_DELIVERY_DECISION_THRESHOLD must be a number between 0 and 1."
        ) from exc

    if threshold < 0 or threshold > 1:
        raise ConfigurationError(
            "LATE_DELIVERY_DECISION_THRESHOLD must be between 0 and 1."
        )

    return threshold


def validate_trigger_token(request_headers) -> None:
    expected_token = os.getenv("INFERENCE_TRIGGER_TOKEN")
    if not expected_token:
        return

    received_token = request_headers.get("x-inference-token")
    if received_token != expected_token:
        raise UnauthorizedError("Missing or invalid inference trigger token.")


def read_json_body(request: BaseHTTPRequestHandler) -> dict:
    content_length = int(request.headers.get("content-length", "0"))
    if content_length == 0:
        return {}

    raw_body = request.rfile.read(content_length)
    if not raw_body:
        return {}

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise BadRequestError("Request body must be valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise BadRequestError("Request body must be a JSON object.")

    return parsed


def normalize_order_ids(raw_order_ids) -> list[int] | None:
    if raw_order_ids is None:
        return None

    if not isinstance(raw_order_ids, list):
        raise BadRequestError("'order_ids' must be an array of integers.")

    normalized: list[int] = []
    for raw_order_id in raw_order_ids:
        try:
            order_id = int(raw_order_id)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("'order_ids' must only contain integers.") from exc

        if order_id <= 0:
            raise BadRequestError("'order_ids' must contain positive integers.")

        normalized.append(order_id)

    return sorted(set(normalized))


def fetch_pending_orders(
    conn: psycopg.Connection,
    order_ids: list[int] | None,
) -> list[PendingOrder]:
    query = FETCH_PENDING_ORDERS_SQL
    params: list[object] = []

    if order_ids is not None:
        if not order_ids:
            return []

        query += " AND o.order_id = ANY(%s)"
        params.append(order_ids)

    query += " ORDER BY o.order_timestamp ASC"

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [PendingOrder(**row) for row in rows]


def store_predictions(
    conn: psycopg.Connection,
    predictions: list[OrderPrediction],
) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            UPSERT_PREDICTIONS_SQL,
            [
                (
                    prediction.order_id,
                    prediction.late_delivery_probability,
                    prediction.predicted_late_delivery,
                )
                for prediction in predictions
            ],
        )


def make_output(
    predictions: list[OrderPrediction],
    decision_threshold: float,
    dry_run: bool,
) -> str:
    summary = summarize_predictions(predictions)

    lines = [
        f"Model: {MODEL_NAME}",
        f"Orders scored: {summary['count']}",
        f"Predicted late: {summary['predicted_late']}",
        f"Decision threshold: {decision_threshold:.2f}",
    ]

    mean_probability = summary["mean_probability"]
    if mean_probability is not None:
        lines.append(f"Mean probability: {mean_probability:.2%}")

    highest_probability = summary["highest_probability"]
    highest_risk_order_id = summary["highest_risk_order_id"]
    if highest_probability is not None and highest_risk_order_id is not None:
        lines.append(
            f"Highest risk order: #{highest_risk_order_id} ({highest_probability:.2%})"
        )

    if dry_run:
        lines.append("Dry run only: predictions were not written to the database.")

    return "\n".join(lines)


def run_inference(request: BaseHTTPRequestHandler) -> tuple[int, dict]:
    validate_trigger_token(request.headers)
    payload = read_json_body(request)
    order_ids = normalize_order_ids(payload.get("order_ids"))
    dry_run = bool(payload.get("dry_run", False))
    decision_threshold = get_decision_threshold()

    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        pending_orders = fetch_pending_orders(conn, order_ids)
        predictions = [
            score_pending_order(order, decision_threshold) for order in pending_orders
        ]

        if predictions and not dry_run:
            store_predictions(conn, predictions)

    output = make_output(predictions, decision_threshold, dry_run)
    message = (
        f"Scored {len(predictions)} unfulfilled orders."
        if predictions
        else "No unfulfilled orders needed scoring."
    )

    return 200, {
        "success": True,
        "message": message,
        "output": output,
        "model": MODEL_NAME,
        "dry_run": dry_run,
        "count": len(predictions),
        "top_predictions": [
            {
                "order_id": prediction.order_id,
                "late_delivery_probability": prediction.late_delivery_probability,
                "predicted_late_delivery": prediction.predicted_late_delivery,
            }
            for prediction in sorted(
                predictions,
                key=lambda prediction: prediction.late_delivery_probability,
                reverse=True,
            )[:5]
        ],
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            threshold = get_decision_threshold()
            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Inference endpoint is healthy.",
                    "model": MODEL_NAME,
                    "decision_threshold": threshold,
                },
            )
        except ConfigurationError as exc:
            self._send_json(500, {"success": False, "message": str(exc)})

    def do_POST(self) -> None:
        try:
            status_code, payload = run_inference(self)
            self._send_json(status_code, payload)
        except BadRequestError as exc:
            self._send_json(400, {"success": False, "message": str(exc)})
        except UnauthorizedError as exc:
            self._send_json(401, {"success": False, "message": str(exc)})
        except ConfigurationError as exc:
            self._send_json(500, {"success": False, "message": str(exc)})
        except Exception as exc:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Inference failed.",
                    "output": str(exc),
                },
            )

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
