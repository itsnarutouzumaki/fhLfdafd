from datetime import datetime, timezone

import pytest

from app.services.metrics import daily_summaries, summarize, to_public_row

UTC = timezone.utc


def test_metrics_calculate_expected_error_values():
    rows = [
        {"forecast_mw": 110, "actual_mw": 100},
        {"forecast_mw": 80, "actual_mw": 100},
    ]
    result = summarize(rows)
    assert result["mae_mw"] == 15
    assert result["rmse_mw"] == pytest.approx(15.81, abs=0.01)
    assert result["bias_mw"] == -5
    assert result["wape_pct"] == 15


def test_missing_pairs_are_excluded_from_error_metrics():
    result = summarize([
        {"forecast_mw": 20, "actual_mw": 10},
        {"forecast_mw": None, "actual_mw": 10},
        {"forecast_mw": 15, "actual_mw": None},
    ])
    assert result["matched_intervals"] == 1
    assert result["actual_intervals"] == 2
    assert result["forecast_intervals"] == 2
    assert result["coverage_pct"] == pytest.approx(100 / 3, abs=0.01)
    assert result["mae_mw"] == 10


def test_zero_actual_denominator_makes_wape_unavailable():
    result = summarize([{"forecast_mw": 12, "actual_mw": 0}])
    assert result["wape_pct"] is None


def test_no_matched_rows_returns_unavailable_metrics():
    result = summarize([{"forecast_mw": None, "actual_mw": 3}])
    assert result["mae_mw"] is None
    assert result["rmse_mw"] is None
    assert result["bias_mw"] is None
    assert result["wape_pct"] is None
    assert result["matched_intervals"] == 0


def test_empty_dataset_has_zero_counts_and_unavailable_percentages():
    result = summarize([])
    assert result["expected_intervals"] == 0
    assert result["coverage_pct"] is None
    assert result["mae_mw"] is None


def test_positive_bias_means_overforecast():
    result = summarize([{"forecast_mw": 120, "actual_mw": 100}])
    assert result["bias_mw"] == 20


def test_daily_summary_aggregates_by_delivery_date():
    rows = [
        {"start_time": datetime(2026, 1, 1, 0, 0, tzinfo=UTC), "forecast_mw": 100, "actual_mw": 80},
        {"start_time": datetime(2026, 1, 1, 0, 30, tzinfo=UTC), "forecast_mw": 90, "actual_mw": 100},
        {"start_time": datetime(2026, 1, 2, 0, 0, tzinfo=UTC), "forecast_mw": None, "actual_mw": 100},
    ]
    result = daily_summaries(rows)
    assert len(result) == 2
    assert result[0]["date"] == "2026-01-01"
    assert result[0]["mae_mw"] == 15
    assert result[1]["mae_mw"] is None


def test_public_row_serializes_timestamps():
    row = {
        "start_time": datetime(2026, 1, 1, tzinfo=UTC),
        "forecast_publish_time": datetime(2025, 12, 31, 8, tzinfo=UTC),
        "decision_cutoff": datetime(2025, 12, 31, 9, tzinfo=UTC),
        "forecast_mw": 100,
    }
    public = to_public_row(row)
    assert public["start_time"] == "2026-01-01T00:00:00Z"
    assert public["forecast_publish_time"] == "2025-12-31T08:00:00Z"


def test_expected_interval_count_is_retained_in_coverage():
    rows = [{"forecast_mw": 1, "actual_mw": 1} for _ in range(48)]
    result = summarize(rows)
    assert result["expected_intervals"] == 48
    assert result["coverage_pct"] == 100
