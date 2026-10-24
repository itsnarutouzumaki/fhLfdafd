from __future__ import annotations

import csv
import io
import re
from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.clients.elexon import ElexonAPIError
from app.config import settings
from app.schemas import AccuracyResponse, DashboardResponse, DataStatus, ForecastDayResponse
from app.services.data_service import WindDataService
from app.services.metrics import daily_summaries, summarize, to_public_row
from app.services.selection import MONTH_END, MONTH_START

app = FastAPI(
    title="Wind Forecast Intelligence Portal API",
    description="Decision-time UK wind generation forecast analysis using Elexon FUELHH and WINDFOR datasets.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)
service = WindDataService()
CUTOFF_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def validate_cutoff(cutoff: str) -> str:
    if not CUTOFF_PATTERN.fullmatch(cutoff):
        raise HTTPException(status_code=422, detail="cutoff must use 24-hour HH:MM format, for example 09:00")
    return cutoff


def validate_day(day: date) -> date:
    if not MONTH_START <= day < MONTH_END:
        raise HTTPException(status_code=422, detail="date must be within January 2026")
    return day


def validate_date_range(start_date: date, end_date: date) -> None:
    if not MONTH_START <= start_date < MONTH_END or not MONTH_START <= end_date < MONTH_END:
        raise HTTPException(status_code=422, detail="start_date and end_date must be within January 2026")
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")


async def load_series(cutoff: str) -> tuple[list[dict[str, Any]], Any]:
    try:
        return await service.get_series(cutoff)
    except ElexonAPIError as exc:
        raise HTTPException(
            status_code=503,
            detail="Elexon data is currently unavailable. Verify upstream connectivity and retry.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Wind forecast data could not be prepared.") from exc


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "wind-forecast-intelligence-portal"}


@app.get("/api/data-status", response_model=DataStatus)
async def data_status() -> dict[str, Any]:
    return await service.data_status()


@app.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard(
    cutoff: str = Query(default="09:00"),
    refresh: bool = Query(default=False),
) -> dict[str, Any]:
    validate_cutoff(cutoff)
    try:
        payload = await service.dashboard(cutoff, force_refresh=refresh)
    except ElexonAPIError as exc:
        raise HTTPException(status_code=503, detail="Elexon data is currently unavailable. Verify upstream connectivity and retry.") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Wind forecast data could not be prepared.") from exc
    payload["series"] = [to_public_row(row) for row in payload["series"]]
    return payload


@app.get("/api/forecast/day", response_model=ForecastDayResponse)
async def forecast_day(
    date_value: date = Query(alias="date"),
    cutoff: str = Query(default="09:00"),
) -> dict[str, Any]:
    day = validate_day(date_value)
    validate_cutoff(cutoff)
    series, snapshot = await load_series(cutoff)
    rows = [row for row in series if row["start_time"].date() == day]
    return {
        "date": day.isoformat(),
        "decision_cutoff": cutoff,
        "retrieved_at": snapshot.retrieved_at.isoformat().replace("+00:00", "Z"),
        "metrics": summarize(rows),
        "intervals": [to_public_row(row) for row in rows],
    }


@app.get("/api/accuracy", response_model=AccuracyResponse)
async def accuracy(
    cutoff: str = Query(default="09:00"),
    start_date: date = Query(default=date(2026, 1, 1)),
    end_date: date = Query(default=date(2026, 1, 31)),
) -> dict[str, Any]:
    validate_cutoff(cutoff)
    validate_date_range(start_date, end_date)
    series, snapshot = await load_series(cutoff)
    rows = [row for row in series if start_date <= row["start_time"].date() <= end_date]
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "decision_cutoff": cutoff,
        "retrieved_at": snapshot.retrieved_at.isoformat().replace("+00:00", "Z"),
        "metrics": summarize(rows),
        "daily_trend": daily_summaries(rows),
        "intervals": [to_public_row(row) for row in rows],
    }


@app.get("/api/export.csv")
async def export_csv(cutoff: str = Query(default="09:00")) -> StreamingResponse:
    validate_cutoff(cutoff)
    series, _ = await load_series(cutoff)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "delivery_start_utc", "decision_cutoff_utc", "forecast_generation_mw",
        "actual_generation_mw", "forecast_error_mw", "absolute_error_mw",
        "forecast_publish_time_utc", "status",
    ])
    for row in series:
        public = to_public_row(row)
        writer.writerow([
            public["start_time"], public["decision_cutoff"], public["forecast_mw"],
            public["actual_mw"], public["error_mw"], public["abs_error_mw"],
            public["forecast_publish_time"], public["status"],
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="wind-forecast-january-2026-{cutoff.replace(":", "")}.csv"'},
    )


static_dir = settings.static_dir
if static_dir.exists() and (static_dir / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}")
    async def frontend(request: Request, path: str) -> Any:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        target = static_dir / path
        if path and target.is_file() and static_dir.resolve() in target.resolve().parents:
            from fastapi.responses import FileResponse
            return FileResponse(target)
        from fastapi.responses import FileResponse
        return FileResponse(static_dir / "index.html")
