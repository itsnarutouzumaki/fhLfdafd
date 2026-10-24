from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx

from app.config import settings

UTC = timezone.utc


class ElexonAPIError(RuntimeError):
    """Raised when Elexon data cannot be retrieved or validated."""


def unpack_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    raise ElexonAPIError("Elexon returned an unexpected response shape; expected a JSON array.")


class ElexonClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(
            base_url=settings.api_base_url,
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "wind-forecast-intelligence-portal/1.0"},
        )
        try:
            last_error: Exception | None = None
            for attempt in range(settings.max_retries + 1):
                try:
                    response = await client.get(path, params=params)
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < settings.max_retries:
                            await asyncio.sleep(min(0.4 * (2**attempt), 3.0))
                            continue
                    response.raise_for_status()
                    return unpack_records(response.json())
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError, ValueError, ElexonAPIError) as exc:
                    last_error = exc
                    retryable = isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or (
                        isinstance(exc, httpx.HTTPStatusError)
                        and (exc.response.status_code == 429 or exc.response.status_code >= 500)
                    )
                    if retryable and attempt < settings.max_retries:
                        await asyncio.sleep(min(0.4 * (2**attempt), 3.0))
                        continue
                    break
            detail = str(last_error or "unknown upstream error")
            raise ElexonAPIError(f"Could not retrieve {path} from Elexon: {detail}") from last_error
        finally:
            if owned_client:
                await client.aclose()

    async def fetch_actuals(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        """Fetch actuals for [start_date, end_date), using week-sized requests."""
        rows: list[dict[str, Any]] = []
        cursor = start_date
        while cursor < end_date:
            chunk_end = min(cursor + timedelta(days=7), end_date)
            # Elexon's settlement date filters are date based and inclusive.
            params = {
                "settlementDateFrom": cursor.isoformat(),
                "settlementDateTo": (chunk_end - timedelta(days=1)).isoformat(),
                "fuelType": "WIND",
            }
            rows.extend(await self._get("/datasets/FUELHH/stream", params))
            cursor = chunk_end
        return self._deduplicate(rows)

    async def fetch_forecasts(self, publication_start: date, publication_end: date) -> list[dict[str, Any]]:
        """Fetch forecast vintages for the half-open publication-date range.

        Requests are split by UTC day to avoid very large responses and to make
        failures easier to retry. Adjacent requests can include a boundary row;
        rows are deduplicated after retrieval.
        """
        days: list[date] = []
        cursor = publication_start
        while cursor < publication_end:
            days.append(cursor)
            cursor += timedelta(days=1)

        semaphore = asyncio.Semaphore(3)

        async def fetch_day(day: date) -> list[dict[str, Any]]:
            async with semaphore:
                day_start = datetime.combine(day, time.min, tzinfo=UTC)
                day_end = day_start + timedelta(days=1)
                return await self._get(
                    "/datasets/WINDFOR/stream",
                    {
                        "publishDateTimeFrom": day_start.isoformat().replace("+00:00", "Z"),
                        "publishDateTimeTo": day_end.isoformat().replace("+00:00", "Z"),
                    },
                )

        results = await asyncio.gather(*(fetch_day(day) for day in days), return_exceptions=True)
        errors = [result for result in results if isinstance(result, Exception)]
        if errors:
            first = errors[0]
            if isinstance(first, ElexonAPIError):
                raise first
            raise ElexonAPIError(f"Could not retrieve historical wind forecast publications: {first}") from first
        rows: list[dict[str, Any]] = []
        for result in results:
            rows.extend(result)  # type: ignore[arg-type]
        return self._deduplicate(rows)

    @staticmethod
    def _deduplicate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str, str, str, str]] = set()
        result: list[dict[str, Any]] = []
        for row in rows:
            signature = (
                str(row.get("startTime", "")),
                str(row.get("publishTime", "")),
                str(row.get("generation", "")),
                str(row.get("fuelType", "")),
                str(row.get("documentId", "")),
            )
            if signature not in seen:
                seen.add(signature)
                result.append(row)
        return result
