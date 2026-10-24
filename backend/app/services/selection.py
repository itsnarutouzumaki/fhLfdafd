from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

UTC = timezone.utc
LONDON = ZoneInfo("Europe/London")
MONTH_START = date(2026, 1, 1)
MONTH_END = date(2026, 2, 1)


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an API timestamp and normalize it to an aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            # Some historical BMRS records use a space before the time but no T.
            try:
                parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S%z")
            except ValueError:
                try:
                    parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def cutoff_for_delivery(delivery_start: datetime, cutoff: str = "09:00") -> datetime:
    """Return the D-1 decision cutoff as an aware UTC timestamp."""
    delivery_local = delivery_start.astimezone(LONDON)
    try:
        hour_text, minute_text = cutoff.split(":", 1)
        cutoff_time = time(int(hour_text), int(minute_text))
    except (ValueError, TypeError) as exc:
        raise ValueError("Cutoff must be HH:MM in 24-hour time") from exc
    decision_date = delivery_local.date() - timedelta(days=1)
    local_cutoff = datetime.combine(decision_date, cutoff_time, tzinfo=LONDON)
    return local_cutoff.astimezone(UTC)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _revision_key(record: dict[str, Any]) -> tuple[datetime, int, str]:
    published = parse_timestamp(record.get("publishTime")) or datetime.min.replace(tzinfo=UTC)
    revision = record.get("documentRevisionNumber") or record.get("revisionNumber") or 0
    try:
        revision_number = int(revision)
    except (TypeError, ValueError):
        revision_number = 0
    return published, revision_number, str(record.get("documentId") or "")


def normalize_actuals(records: Iterable[dict[str, Any]]) -> dict[datetime, float]:
    """Return the latest available actual generation per UTC delivery interval."""
    selected: dict[datetime, tuple[tuple[datetime, int, str], float]] = {}
    for record in records:
        fuel = str(record.get("fuelType", "")).strip().upper()
        if fuel != "WIND":
            continue
        start = parse_timestamp(record.get("startTime"))
        generation = _number(record.get("generation"))
        if start is None or generation is None:
            continue
        key = _revision_key(record)
        if start not in selected or key >= selected[start][0]:
            selected[start] = (key, generation)
    return {start: value for start, (_, value) in selected.items()}


def normalize_forecasts(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize forecast rows while retaining publication timestamps and revisions."""
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[datetime, datetime, float, str]] = set()
    for record in records:
        start = parse_timestamp(record.get("startTime"))
        published = parse_timestamp(record.get("publishTime"))
        generation = _number(record.get("generation"))
        if start is None or published is None or generation is None:
            continue
        signature = (start, published, generation, str(record.get("documentId") or ""))
        if signature in seen:
            continue
        seen.add(signature)
        normalized.append(
            {
                "start_time": start,
                "publish_time": published,
                "generation_mw": generation,
                "revision": record.get("documentRevisionNumber") or record.get("revisionNumber") or 0,
                "document_id": str(record.get("documentId") or ""),
            }
        )
    return normalized


def build_series(
    actual_records: Iterable[dict[str, Any]],
    forecast_records: Iterable[dict[str, Any]],
    cutoff: str = "09:00",
    start_date: date = MONTH_START,
    end_date: date = MONTH_END,
) -> list[dict[str, Any]]:
    """Build a half-hourly delivery series using only eligible forecast vintages.

    The date range is start-inclusive and end-exclusive. Each forecast is chosen
    independently for its delivery interval using the D-1 decision cutoff.
    """
    if start_date >= end_date:
        raise ValueError("start_date must be earlier than end_date")
    actuals = normalize_actuals(actual_records)
    forecasts = normalize_forecasts(forecast_records)
    forecasts_by_start: dict[datetime, list[dict[str, Any]]] = {}
    for forecast in forecasts:
        forecasts_by_start.setdefault(forecast["start_time"], []).append(forecast)

    cursor = datetime.combine(start_date, time.min, tzinfo=UTC)
    end = datetime.combine(end_date, time.min, tzinfo=UTC)
    result: list[dict[str, Any]] = []
    while cursor < end:
        deadline = cutoff_for_delivery(cursor, cutoff)
        eligible = [item for item in forecasts_by_start.get(cursor, []) if item["publish_time"] <= deadline]
        selected: dict[str, Any] | None = None
        if eligible:
            selected = max(
                eligible,
                key=lambda item: (
                    item["publish_time"],
                    int(item["revision"]) if str(item["revision"]).isdigit() else 0,
                    item["document_id"],
                ),
            )
        actual = actuals.get(cursor)
        forecast_value = selected["generation_mw"] if selected else None
        error = forecast_value - actual if forecast_value is not None and actual is not None else None
        if forecast_value is not None and actual is not None:
            status = "matched"
        elif forecast_value is None and actual is not None:
            status = "forecast_missing"
        elif forecast_value is not None and actual is None:
            status = "actual_missing"
        else:
            status = "both_missing"
        result.append(
            {
                "start_time": cursor,
                "forecast_mw": forecast_value,
                "actual_mw": actual,
                "error_mw": error,
                "abs_error_mw": abs(error) if error is not None else None,
                "forecast_publish_time": selected["publish_time"] if selected else None,
                "decision_cutoff": deadline,
                "status": status,
            }
        )
        cursor += timedelta(minutes=30)
    return result
