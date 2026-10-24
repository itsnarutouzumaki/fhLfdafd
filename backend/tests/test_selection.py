from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.selection import (
    MONTH_END, MONTH_START, build_series, cutoff_for_delivery, parse_timestamp,
)

UTC = timezone.utc


def test_january_contains_expected_half_hourly_intervals():
    rows = build_series([], [])
    assert len(rows) == 1488
    assert rows[0]["start_time"] == datetime(2026, 1, 1, tzinfo=UTC)
    assert rows[-1]["start_time"] == datetime(2026, 1, 31, 23, 30, tzinfo=UTC)


def test_first_january_interval_uses_december_31_cutoff():
    delivery = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert cutoff_for_delivery(delivery, "09:00") == datetime(2025, 12, 31, 9, 0, tzinfo=UTC)


def test_latest_eligible_forecast_is_selected_and_later_vintage_is_excluded():
    delivery = "2026-01-01T10:00:00Z"
    forecasts = [
        {"startTime": delivery, "publishTime": "2025-12-31T08:30:00Z", "generation": 1800},
        {"startTime": delivery, "publishTime": "2025-12-31T09:00:00Z", "generation": 1900},
        {"startTime": delivery, "publishTime": "2025-12-31T09:01:00Z", "generation": 9999},
    ]
    rows = build_series([], forecasts)
    target = next(row for row in rows if row["start_time"].isoformat() == "2026-01-01T10:00:00+00:00")
    assert target["forecast_mw"] == 1900
    assert target["forecast_publish_time"] == datetime(2025, 12, 31, 9, 0, tzinfo=UTC)


def test_forecast_published_exactly_at_cutoff_is_eligible():
    forecast = {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T09:00:00Z", "generation": 1}
    row = build_series([], [forecast])[0]
    assert row["forecast_mw"] == 1


def test_no_forecast_before_cutoff_remains_missing():
    forecast = {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T09:00:01Z", "generation": 100}
    row = build_series([], [forecast])[0]
    assert row["forecast_mw"] is None
    assert row["status"] == "both_missing"


def test_join_is_by_timestamp_not_list_order():
    actuals = [
        {"startTime": "2026-01-01T00:30:00Z", "fuelType": "WIND", "generation": 51},
        {"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": 40},
    ]
    forecasts = [
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T08:00:00Z", "generation": 41},
        {"startTime": "2026-01-01T00:30:00Z", "publishTime": "2025-12-31T08:00:00Z", "generation": 54},
    ]
    rows = build_series(actuals, forecasts)
    assert rows[0]["actual_mw"] == 40
    assert rows[0]["forecast_mw"] == 41
    assert rows[1]["actual_mw"] == 51
    assert rows[1]["forecast_mw"] == 54


def test_latest_actual_revision_wins():
    actuals = [
        {"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": 30, "publishTime": "2026-01-02T00:00:00Z"},
        {"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": 35, "publishTime": "2026-01-03T00:00:00Z"},
    ]
    row = build_series(actuals, [])[0]
    assert row["actual_mw"] == 35


def test_non_wind_actuals_are_ignored():
    actuals = [{"startTime": "2026-01-01T00:00:00Z", "fuelType": "GAS", "generation": 300}]
    assert build_series(actuals, [])[0]["actual_mw"] is None


def test_duplicate_identical_forecasts_do_not_change_selected_value():
    forecast = {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T08:00:00Z", "generation": 120}
    row = build_series([], [forecast, forecast])[0]
    assert row["forecast_mw"] == 120


def test_invalid_generation_is_ignored():
    actuals = [{"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": "null"}]
    assert build_series(actuals, [])[0]["actual_mw"] is None


def test_missing_actual_with_forecast_has_clear_status():
    forecasts = [{"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T08:00:00Z", "generation": 42}]
    row = build_series([], forecasts)[0]
    assert row["status"] == "actual_missing"
    assert row["error_mw"] is None


def test_invalid_cutoff_is_rejected():
    with pytest.raises(ValueError):
        cutoff_for_delivery(datetime(2026, 1, 1, tzinfo=UTC), "25:99")


def test_start_date_inclusive_end_date_exclusive():
    rows = build_series([], [], start_date=date(2026, 1, 2), end_date=date(2026, 1, 3))
    assert len(rows) == 48
    assert rows[0]["start_time"].date() == date(2026, 1, 2)
    assert rows[-1]["start_time"].date() == date(2026, 1, 2)


def test_timestamps_with_naive_api_format_are_interpreted_as_utc():
    assert parse_timestamp("2026-01-01 00:00:00") == datetime(2026, 1, 1, tzinfo=UTC)


def test_dst_cutoff_uses_london_timezone_rules():
    # On 1 April 2026, 09:00 D-1 falls in British Summer Time (UTC+1).
    deadline = cutoff_for_delivery(datetime(2026, 4, 1, 0, 0, tzinfo=UTC), "09:00")
    assert deadline == datetime(2026, 3, 31, 8, 0, tzinfo=UTC)
