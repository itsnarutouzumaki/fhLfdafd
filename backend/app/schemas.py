from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Metrics(BaseModel):
    expected_intervals: int
    actual_intervals: int
    forecast_intervals: int
    matched_intervals: int
    coverage_pct: float | None
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    wape_pct: float | None


class DailyTrend(BaseModel):
    date: str
    mae_mw: float | None
    bias_mw: float | None
    matched_intervals: int
    forecast_avg_mw: float | None
    actual_avg_mw: float | None


class SourceStatus(BaseModel):
    status: Literal["connected", "partial", "empty"]
    actual_records_received: int = 0
    forecast_records_received: int = 0
    message: str
    actual_error: str | None = None
    forecast_error: str | None = None


class DataStatus(SourceStatus):
    status: Literal["connected", "partial", "empty", "unavailable"]
    retrieved_at: str | None = None
    detail: str | None = None


class ForecastInterval(BaseModel):
    start_time: str
    forecast_mw: float | None
    actual_mw: float | None
    error_mw: float | None
    abs_error_mw: float | None
    forecast_publish_time: str | None
    decision_cutoff: str
    status: Literal["matched", "forecast_missing", "actual_missing", "both_missing"]


class EvaluationPeriod(BaseModel):
    start: str
    end_exclusive: str


class DashboardResponse(BaseModel):
    generated_at: str
    retrieved_at: str
    evaluation_period: EvaluationPeriod
    decision_cutoff: str
    metrics: Metrics
    daily_trend: list[DailyTrend]
    series: list[ForecastInterval]
    source_status: SourceStatus


class ForecastDayResponse(BaseModel):
    date: str
    decision_cutoff: str
    retrieved_at: str
    metrics: Metrics
    intervals: list[ForecastInterval]


class AccuracyResponse(BaseModel):
    start_date: str
    end_date: str
    decision_cutoff: str
    retrieved_at: str
    metrics: Metrics
    daily_trend: list[DailyTrend]
    intervals: list[ForecastInterval]
