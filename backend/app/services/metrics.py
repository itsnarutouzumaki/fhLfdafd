from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import sqrt
from typing import Any, Iterable


def summarize(series: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(series)
    matched = [row for row in rows if row.get("forecast_mw") is not None and row.get("actual_mw") is not None]
    actual_count = sum(row.get("actual_mw") is not None for row in rows)
    forecast_count = sum(row.get("forecast_mw") is not None for row in rows)
    errors = [float(row["forecast_mw"]) - float(row["actual_mw"]) for row in matched]
    actual_sum = sum(float(row["actual_mw"]) for row in matched)
    absolute_error_sum = sum(abs(error) for error in errors)
    count = len(matched)
    return {
        "expected_intervals": len(rows),
        "actual_intervals": actual_count,
        "forecast_intervals": forecast_count,
        "matched_intervals": count,
        "coverage_pct": round(100 * count / len(rows), 2) if rows else None,
        "mae_mw": round(sum(abs(error) for error in errors) / count, 2) if count else None,
        "rmse_mw": round(sqrt(sum(error * error for error in errors) / count), 2) if count else None,
        "bias_mw": round(sum(errors) / count, 2) if count else None,
        "wape_pct": round(100 * absolute_error_sum / actual_sum, 2) if count and actual_sum > 0 else None,
    }


def daily_summaries(series: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in series:
        timestamp = row["start_time"]
        if isinstance(timestamp, datetime):
            key = timestamp.date().isoformat()
        else:
            key = str(timestamp)[:10]
        grouped[key].append(row)

    result: list[dict[str, Any]] = []
    for day in sorted(grouped):
        rows = grouped[day]
        metrics = summarize(rows)
        actual_values = [row["actual_mw"] for row in rows if row.get("actual_mw") is not None]
        forecast_values = [row["forecast_mw"] for row in rows if row.get("forecast_mw") is not None]
        result.append(
            {
                "date": day,
                "mae_mw": metrics["mae_mw"],
                "bias_mw": metrics["bias_mw"],
                "matched_intervals": metrics["matched_intervals"],
                "forecast_avg_mw": round(sum(forecast_values) / len(forecast_values), 2) if forecast_values else None,
                "actual_avg_mw": round(sum(actual_values) / len(actual_values), 2) if actual_values else None,
            }
        )
    return result


def to_public_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert internal datetime values to ISO timestamps for API responses."""
    return {
        **row,
        "start_time": row["start_time"].isoformat().replace("+00:00", "Z") if isinstance(row.get("start_time"), datetime) else row.get("start_time"),
        "forecast_publish_time": row["forecast_publish_time"].isoformat().replace("+00:00", "Z") if isinstance(row.get("forecast_publish_time"), datetime) else row.get("forecast_publish_time"),
        "decision_cutoff": row["decision_cutoff"].isoformat().replace("+00:00", "Z") if isinstance(row.get("decision_cutoff"), datetime) else row.get("decision_cutoff"),
    }
