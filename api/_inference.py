from __future__ import annotations

from dataclasses import dataclass
import math

DEFAULT_DECISION_THRESHOLD = 0.5
HISTORICAL_RATE_PRIOR_WEIGHT = 5.0


@dataclass(frozen=True)
class PendingOrder:
    order_id: int
    order_age_hours: float
    num_items: int
    total_value: float
    avg_weight: float
    prior_shipments: int
    prior_late_shipments: int
    avg_promised_days: float
    avg_actual_days: float
    avg_delivery_gap: float
    overall_late_rate: float


@dataclass(frozen=True)
class OrderPrediction:
    order_id: int
    late_delivery_probability: float
    predicted_late_delivery: int


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-value)
        return 1.0 / (1.0 + exponent)

    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def smoothed_late_rate(order: PendingOrder) -> float:
    baseline = clamp(order.overall_late_rate, 0.05, 0.95)
    return (order.prior_late_shipments + (baseline * HISTORICAL_RATE_PRIOR_WEIGHT)) / (
        order.prior_shipments + HISTORICAL_RATE_PRIOR_WEIGHT
    )


def score_pending_order(
    order: PendingOrder,
    decision_threshold: float = DEFAULT_DECISION_THRESHOLD,
) -> OrderPrediction:
    historical_rate = smoothed_late_rate(order)
    normalized_age = clamp(order.order_age_hours / 24.0, 0.0, 7.0)
    normalized_items = clamp(order.num_items / 6.0, 0.0, 4.0)
    normalized_value = clamp(order.total_value / 250.0, 0.0, 4.0)
    normalized_weight = clamp(order.avg_weight / 12.0, 0.0, 4.0)
    normalized_gap = clamp(max(order.avg_delivery_gap, 0.0), 0.0, 4.0)
    normalized_promised_days = clamp(order.avg_promised_days / 5.0, 0.0, 4.0)

    score = -2.0
    score += 1.85 * historical_rate
    score += 0.45 * normalized_age
    score += 0.25 * normalized_items
    score += 0.20 * normalized_value
    score += 0.30 * normalized_weight
    score += 0.25 * normalized_gap
    score += 0.15 * normalized_promised_days

    probability = sigmoid(score)
    probability = clamp(probability, 0.001, 0.999)

    return OrderPrediction(
        order_id=order.order_id,
        late_delivery_probability=round(probability, 6),
        predicted_late_delivery=int(probability >= decision_threshold),
    )


def summarize_predictions(
    predictions: list[OrderPrediction],
) -> dict[str, float | int | None]:
    if not predictions:
        return {
            "count": 0,
            "predicted_late": 0,
            "mean_probability": None,
            "highest_risk_order_id": None,
            "highest_probability": None,
        }

    predicted_late = sum(pred.predicted_late_delivery for pred in predictions)
    mean_probability = sum(
        pred.late_delivery_probability for pred in predictions
    ) / len(predictions)
    highest_risk = max(predictions, key=lambda pred: pred.late_delivery_probability)

    return {
        "count": len(predictions),
        "predicted_late": predicted_late,
        "mean_probability": round(mean_probability, 6),
        "highest_risk_order_id": highest_risk.order_id,
        "highest_probability": highest_risk.late_delivery_probability,
    }
