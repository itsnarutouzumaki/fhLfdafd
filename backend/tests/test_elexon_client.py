from datetime import date

import httpx
import pytest

from app.clients.elexon import ElexonAPIError, ElexonClient, unpack_records


def test_unpack_records_accepts_array_and_wrapped_response():
    assert unpack_records([{"generation": 1}]) == [{"generation": 1}]
    assert unpack_records({"data": [{"generation": 2}]}) == [{"generation": 2}]


def test_unpack_records_rejects_unknown_schema():
    with pytest.raises(ElexonAPIError):
        unpack_records({"results": []})


@pytest.mark.asyncio
async def test_actual_request_uses_documented_fuel_filters():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(base_url="https://example.test", transport=httpx.MockTransport(handler)) as http_client:
        client = ElexonClient(http_client)
        await client.fetch_actuals(date(2026, 1, 1), date(2026, 1, 2))
    assert len(seen) == 1
    assert seen[0].url.path == "/datasets/FUELHH/stream"
    assert seen[0].url.params["fuelType"] == "WIND"
    assert seen[0].url.params["settlementDateFrom"] == "2026-01-01"
    assert seen[0].url.params["settlementDateTo"] == "2026-01-01"


@pytest.mark.asyncio
async def test_forecast_request_uses_publication_time_filters():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(base_url="https://example.test", transport=httpx.MockTransport(handler)) as http_client:
        client = ElexonClient(http_client)
        await client.fetch_forecasts(date(2025, 12, 31), date(2026, 1, 1))
    assert len(seen) == 1
    assert seen[0].url.path == "/datasets/WINDFOR/stream"
    assert seen[0].url.params["publishDateTimeFrom"] == "2025-12-31T00:00:00Z"
    assert seen[0].url.params["publishDateTimeTo"] == "2026-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_non_success_upstream_response_becomes_domain_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad query")

    async with httpx.AsyncClient(base_url="https://example.test", transport=httpx.MockTransport(handler)) as http_client:
        client = ElexonClient(http_client)
        with pytest.raises(ElexonAPIError):
            await client._get("/datasets/FUELHH/stream", {"fuelType": "WIND"})
