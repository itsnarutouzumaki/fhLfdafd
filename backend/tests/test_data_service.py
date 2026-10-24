from datetime import date

import pytest

from app.clients.elexon import ElexonAPIError
from app.services.data_service import WindDataService


class PartiallyAvailableClient:
    async def fetch_actuals(self, start_date: date, end_date: date):
        return [{"startTime": "2026-01-01T00:00:00Z", "fuelType": "WIND", "generation": 100}]

    async def fetch_forecasts(self, publication_start: date, publication_end: date):
        raise ElexonAPIError("forecast endpoint timed out")


class UnavailableClient:
    async def fetch_actuals(self, start_date: date, end_date: date):
        raise ElexonAPIError("actual endpoint unavailable")

    async def fetch_forecasts(self, publication_start: date, publication_end: date):
        raise ElexonAPIError("forecast endpoint unavailable")


@pytest.mark.asyncio
async def test_partial_source_failure_keeps_successful_actuals_and_reports_partial_status():
    service = WindDataService(PartiallyAvailableClient())
    dashboard = await service.dashboard()
    assert dashboard["source_status"]["status"] == "partial"
    assert dashboard["source_status"]["actual_records_received"] == 1
    assert dashboard["source_status"]["forecast_records_received"] == 0
    assert dashboard["source_status"]["forecast_error"] == "forecast endpoint timed out"
    assert dashboard["metrics"]["actual_intervals"] == 1


@pytest.mark.asyncio
async def test_failure_of_both_sources_is_reported_as_unavailable():
    service = WindDataService(UnavailableClient())
    status = await service.data_status()
    assert status["status"] == "unavailable"
    assert "actual endpoint unavailable" in status["detail"]
