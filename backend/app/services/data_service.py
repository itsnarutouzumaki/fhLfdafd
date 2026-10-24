from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from app.clients.elexon import ElexonAPIError, ElexonClient
from app.config import settings
from app.services.metrics import daily_summaries, summarize
from app.services.selection import MONTH_END, MONTH_START, build_series

UTC = timezone.utc


@dataclass
class Snapshot:
    actuals: list[dict[str, Any]]
    forecasts: list[dict[str, Any]]
    retrieved_at: datetime
    actual_error: str | None = None
    forecast_error: str | None = None


class WindDataService:
    def __init__(self, client: ElexonClient | None = None) -> None:
        self.client = client or ElexonClient()
        self._snapshot: Snapshot | None = None
        self._lock = asyncio.Lock()
        self._last_error: str | None = None

    async def _load_snapshot(self, force_refresh: bool = False) -> Snapshot:
        now = datetime.now(UTC)
        if not force_refresh and self._snapshot and (now - self._snapshot.retrieved_at).total_seconds() < settings.cache_ttl_seconds:
            return self._snapshot
        async with self._lock:
            now = datetime.now(UTC)
            if not force_refresh and self._snapshot and (now - self._snapshot.retrieved_at).total_seconds() < settings.cache_ttl_seconds:
                return self._snapshot
            actual_result, forecast_result = await asyncio.gather(
                self.client.fetch_actuals(MONTH_START, MONTH_END),
                # D−1 publication dates for January delivery run from Dec 31 through Jan 30.
                self.client.fetch_forecasts(date(2025, 12, 31), date(2026, 1, 31)),
                return_exceptions=True,
            )
            actual_error = str(actual_result) if isinstance(actual_result, Exception) else None
            forecast_error = str(forecast_result) if isinstance(forecast_result, Exception) else None
            if actual_error and forecast_error:
                self._last_error = f"Actual generation request failed: {actual_error}; forecast request failed: {forecast_error}"
                raise ElexonAPIError(self._last_error)

            actuals = [] if actual_error else actual_result
            forecasts = [] if forecast_error else forecast_result
            snapshot = Snapshot(
                actuals=actuals,  # type: ignore[arg-type]
                forecasts=forecasts,  # type: ignore[arg-type]
                retrieved_at=datetime.now(UTC),
                actual_error=actual_error,
                forecast_error=forecast_error,
            )
            self._snapshot = snapshot
            self._last_error = actual_error or forecast_error
            return snapshot

    @staticmethod
    def _source_status(snapshot: Snapshot) -> dict[str, Any]:
        both_succeeded = snapshot.actual_error is None and snapshot.forecast_error is None
        if both_succeeded and snapshot.actuals and snapshot.forecasts:
            status = "connected"
            message = "Both Elexon datasets returned records."
        elif snapshot.actual_error or snapshot.forecast_error:
            status = "partial"
            problems = []
            if snapshot.actual_error:
                problems.append("Actual-generation retrieval failed")
            if snapshot.forecast_error:
                problems.append("Forecast retrieval failed")
            message = "; ".join(problems) + ". Results include only the source data that could be retrieved."
        elif snapshot.actuals or snapshot.forecasts:
            status = "partial"
            message = "Elexon returned records from only one of the two required datasets."
        else:
            status = "empty"
            message = "Elexon returned no rows for the requested period."
        return {
            "status": status,
            "actual_records_received": len(snapshot.actuals),
            "forecast_records_received": len(snapshot.forecasts),
            "message": message,
            "actual_error": snapshot.actual_error,
            "forecast_error": snapshot.forecast_error,
        }

    async def get_series(self, cutoff: str = "09:00", force_refresh: bool = False) -> tuple[list[dict[str, Any]], Snapshot]:
        snapshot = await self._load_snapshot(force_refresh=force_refresh)
        series = build_series(snapshot.actuals, snapshot.forecasts, cutoff=cutoff)
        return series, snapshot

    async def dashboard(self, cutoff: str = "09:00", force_refresh: bool = False) -> dict[str, Any]:
        series, snapshot = await self.get_series(cutoff, force_refresh=force_refresh)
        return {
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "retrieved_at": snapshot.retrieved_at.isoformat().replace("+00:00", "Z"),
            "evaluation_period": {"start": "2026-01-01", "end_exclusive": "2026-02-01"},
            "decision_cutoff": cutoff,
            "metrics": summarize(series),
            "daily_trend": daily_summaries(series),
            "series": series,
            "source_status": self._source_status(snapshot),
        }

    async def data_status(self) -> dict[str, Any]:
        try:
            snapshot = await self._load_snapshot()
            return {
                **self._source_status(snapshot),
                "retrieved_at": snapshot.retrieved_at.isoformat().replace("+00:00", "Z"),
            }
        except Exception as exc:
            return {
                "status": "unavailable",
                "retrieved_at": self._snapshot.retrieved_at.isoformat().replace("+00:00", "Z") if self._snapshot else None,
                "actual_records_received": len(self._snapshot.actuals) if self._snapshot else 0,
                "forecast_records_received": len(self._snapshot.forecasts) if self._snapshot else 0,
                "message": "Elexon data could not be retrieved. Check the upstream API connection and try again.",
                "detail": str(exc),
            }

    def last_error(self) -> str | None:
        return self._last_error
