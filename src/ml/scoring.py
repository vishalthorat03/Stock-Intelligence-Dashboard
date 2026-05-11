"""
Machine learning scoring and market-wide prediction helpers.
"""
from __future__ import annotations

from math import tanh

import os
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from config.settings import MOMENTUM_WEIGHT, MOMENTUM_WINDOW, SENTIMENT_WEIGHT, VOLUME_WEIGHT
from src.api.logger import setup_logger

logger = setup_logger(__name__, "ml.log")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


def normalize_score(value, min_val=0, max_val=100):
    if max_val == min_val:
        return 50.0
    normalized = ((value - min_val) / (max_val - min_val)) * 100
    return max(0.0, min(100.0, normalized))


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_momentum(price_history):
    if not price_history or len(price_history) < 2:
        return 50.0

    prices = np.array(price_history[-MOMENTUM_WINDOW:], dtype=float)
    returns = np.diff(prices) / prices[:-1]
    if len(returns) == 0:
        return 50.0

    recent_mean = float(np.mean(returns))
    stability_penalty = float(np.std(returns))
    adjusted_momentum = recent_mean - (0.35 * stability_penalty)
    return normalize_score(adjusted_momentum, -0.08, 0.08)


def calculate_volume_signal(volume_history, price_changes):
    if not volume_history or not price_changes:
        return 50.0

    recent_volumes = np.array(volume_history[-20:], dtype=float)
    recent_changes = np.array(price_changes[-20:], dtype=float)
    if len(recent_volumes) == 0 or len(recent_changes) == 0:
        return 50.0

    baseline = np.mean(recent_volumes) or 1.0
    bullish = 0.0
    for volume, change in zip(recent_volumes, recent_changes):
        volume_ratio = volume / baseline
        if change > 0:
            bullish += min(1.5, volume_ratio)
        elif change < 0:
            bullish -= min(1.5, volume_ratio) * 0.75

    signal = bullish / max(len(recent_changes), 1)
    return normalize_score(signal, -1.0, 1.0)


def calculate_composite_score(momentum, volume_signal, sentiment):
    sentiment_normalized = normalize_score(sentiment, -1, 1)
    score = (
        safe_float(momentum) * MOMENTUM_WEIGHT
        + safe_float(volume_signal) * VOLUME_WEIGHT
        + sentiment_normalized * SENTIMENT_WEIGHT
    )
    return max(0.0, min(100.0, score))


def calculate_price_change_series(price_history):
    if not price_history or len(price_history) < 2:
        return []
    prices = np.array(price_history, dtype=float)
    return list(np.diff(prices) / prices[:-1] * 100.0)


def derive_sentiment_proxy(price_history):
    changes = calculate_price_change_series(price_history[-10:])
    if not changes:
        return 0.0
    average_change = np.mean(changes)
    return float(max(-1.0, min(1.0, tanh(average_change / 3.0))))


def build_feature_vector(row):
    return [
        safe_float(row.get("score")),
        safe_float(row.get("momentum")),
        safe_float(row.get("volume_signal")),
        safe_float(row.get("sentiment")),
        safe_float(row.get("price_change")),
        safe_float(row.get("current_price")),
    ]


def prepare_training_examples(history_rows):
    if not history_rows or len(history_rows) < 6:
        return np.array([]), np.array([])

    rows = sorted(history_rows, key=lambda row: row["snapshot_time"])
    features = []
    targets = []
    for current_row, next_row in zip(rows[:-1], rows[1:]):
        features.append(build_feature_vector(current_row))
        targets.append(safe_float(next_row.get("price_change")))
    return np.array(features, dtype=float), np.array(targets, dtype=float)


def build_market_training_dataset(snapshot_rows):
    rows_by_symbol = {}
    for row in snapshot_rows or []:
        rows_by_symbol.setdefault(row["symbol"], []).append(row)

    features = []
    targets = []
    for history_rows in rows_by_symbol.values():
        x_rows, y_rows = prepare_training_examples(history_rows)
        if len(x_rows) == 0:
            continue
        features.extend(x_rows.tolist())
        targets.extend(y_rows.tolist())

    if not features:
        return np.array([]), np.array([])
    return np.array(features, dtype=float), np.array(targets, dtype=float)


def candidate_models():
    return [
        (
            "ExtraTreesRegressor",
            ExtraTreesRegressor(
                n_estimators=180,
                max_depth=8,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=1,
            ),
        ),
        (
            "RandomForestRegressor",
            RandomForestRegressor(
                n_estimators=140,
                max_depth=7,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=1,
            ),
        ),
    ]


def select_best_model(features, targets):
    if len(features) < 20 or len(targets) < 20:
        return None, {
            "model_name": "heuristic",
            "samples": int(len(features)),
            "r2": 0.0,
            "mae": 0.0,
            "status": "not_enough_history",
        }

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        targets,
        test_size=0.25,
        random_state=42,
    )

    best_model = None
    best_meta = None
    best_score = float("-inf")

    for model_name, model in candidate_models():
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        r2 = float(r2_score(y_test, predictions))
        mae = float(mean_absolute_error(y_test, predictions))
        model_score = r2 - (mae * 0.05)

        logger.info("Candidate model %s r2=%.4f mae=%.4f", model_name, r2, mae)

        if model_score > best_score:
            best_score = model_score
            best_model = model
            best_meta = {
                "model_name": model_name,
                "samples": int(len(features)),
                "r2": round(r2, 4),
                "mae": round(mae, 4),
                "status": "trained",
            }

    return best_model, best_meta


def train_price_change_model(snapshot_rows):
    features, targets = build_market_training_dataset(snapshot_rows)
    return select_best_model(features, targets)


def predict_price_change(model, model_meta, stock_row, history_rows):
    heuristic = 0.0
    heuristic += (safe_float(stock_row.get("momentum")) - 50.0) / 18.0
    heuristic += (safe_float(stock_row.get("volume_signal")) - 50.0) / 28.0
    heuristic += safe_float(stock_row.get("sentiment")) * 2.5
    heuristic += safe_float(stock_row.get("price_change")) * 0.2

    volatility = np.std([safe_float(item.get("price_change")) for item in history_rows[-10:]]) if history_rows else 0.0
    model_quality = safe_float((model_meta or {}).get("r2"), 0.0)
    baseline_confidence = max(30.0, min(92.0, 70.0 - volatility * 8.0 + model_quality * 20.0 + len(history_rows) * 1.3))

    if model is None:
        return round(heuristic, 2), round(baseline_confidence, 2)

    feature_row = np.array([build_feature_vector(stock_row)], dtype=float)
    predicted = float(model.predict(feature_row)[0])
    blend = 0.75 if model_quality > 0 else 0.55
    combined = (predicted * blend) + (heuristic * (1 - blend))
    return round(combined, 2), round(baseline_confidence, 2)


def explain_stock(symbol, score, sentiment, momentum, volume_signal, price_change, predicted_price_change, confidence, model_meta=None):
    drivers = []
    if momentum >= 65:
        drivers.append("strong momentum")
    elif momentum <= 40:
        drivers.append("weak momentum")

    if volume_signal >= 60:
        drivers.append("supportive volume")
    elif volume_signal <= 40:
        drivers.append("soft volume conviction")

    if sentiment >= 0.25:
        drivers.append("positive market tone")
    elif sentiment <= -0.25:
        drivers.append("negative market tone")

    if predicted_price_change >= 1.5:
        drivers.append("model expects near-term upside")
    elif predicted_price_change <= -1.5:
        drivers.append("model expects downside risk")

    if not drivers:
        drivers.append("balanced mixed signals")

    if score >= 75:
        stance = "Strong Buy"
    elif score >= 60:
        stance = "Buy"
    elif score >= 45:
        stance = "Hold"
    else:
        stance = "Reduce"

    model_name = (model_meta or {}).get("model_name", "heuristic")
    comparison = {
        "momentum_score": round(momentum, 2),
        "volume_score": round(volume_signal, 2),
        "sentiment_score": round(normalize_score(sentiment, -1, 1), 2),
        "recent_price_change": round(price_change, 2),
        "predicted_price_change": round(predicted_price_change, 2),
        "confidence": round(confidence, 2),
        "model_name": model_name,
    }

    summary = (
        f"{symbol} ranks on {', '.join(drivers)}. Composite score {score:.1f}, "
        f"predicted move {predicted_price_change:.2f}% using {model_name}, confidence {confidence:.0f}%."
    )

    return {
        "stance": stance,
        "summary": summary,
        "drivers": drivers,
        "comparison": comparison,
        "model_name": model_name,
    }


def generate_insight(score, sentiment, momentum, price_change):
    if score >= 75:
        strength = "Strong Buy"
    elif score >= 60:
        strength = "Buy"
    elif score >= 40:
        strength = "Hold"
    else:
        strength = "Sell"

    if momentum >= 60:
        momentum_text = "strong upward momentum"
    elif momentum >= 40:
        momentum_text = "moderate trend strength"
    else:
        momentum_text = "downward pressure"

    if sentiment > 0.3:
        sentiment_text = "positive sentiment"
    elif sentiment < -0.3:
        sentiment_text = "negative sentiment"
    else:
        sentiment_text = "mixed sentiment"

    if price_change > 2:
        price_text = f"up {price_change:.1f}% recently"
    elif price_change < -2:
        price_text = f"down {abs(price_change):.1f}% recently"
    else:
        price_text = "stable recently"

    return f"{strength}: {momentum_text}, {sentiment_text}, {price_text}."
