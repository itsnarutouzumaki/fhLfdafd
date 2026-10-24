#!/usr/bin/env python3
"""Probe the documented Elexon datasets and summarize real response shapes.

Run from the repository root after installing backend dependencies:
    python scripts/verify_elexon.py

This script intentionally does not write source data to disk or create demo rows.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"


def unpack(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return [row for row in payload["data"] if isinstance(row, dict)]
    raise ValueError(f"Unrecognized response type: {type(payload).__name__}")


def probe(client: httpx.Client, label: str, path: str, params: dict[str, str]) -> list[dict]:
    print(f"\n{label}: GET {path}")
    print(f"Parameters: {json.dumps(params, sort_keys=True)}")
    response = client.get(path, params=params)
    print(f"HTTP status: {response.status_code}")
    response.raise_for_status()
    rows = unpack(response.json())
    print(f"Records returned: {len(rows)}")
    if rows:
        print(f"First record fields: {', '.join(sorted(rows[0].keys()))}")
        print(f"First record sample: {json.dumps(rows[0], default=str)[:700]}")
    else:
        print("The request succeeded, but returned no records for this sample period.")
    return rows


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=25, headers={"Accept": "application/json", "User-Agent": "wind-forecast-intelligence-portal-verification/1.0"})
    try:
        actuals = probe(
            client,
            "FUELHH actual generation",
            "/datasets/FUELHH/stream",
            {"settlementDateFrom": "2026-01-01", "settlementDateTo": "2026-01-01", "fuelType": "WIND"},
        )
        forecasts = probe(
            client,
            "WINDFOR historical forecast publications",
            "/datasets/WINDFOR/stream",
            {"publishDateTimeFrom": "2025-12-31T00:00:00Z", "publishDateTimeTo": "2026-01-01T00:00:00Z"},
        )
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        print(f"\nElexon verification failed: {exc}", file=sys.stderr)
        print("Check network access and rerun. The application must not present synthetic records as real data.", file=sys.stderr)
        return 1
    finally:
        client.close()

    if actuals and not any(str(row.get("fuelType", "")).upper() == "WIND" for row in actuals):
        print("WARNING: the actuals sample contained no explicit WIND fuelType value. Inspect its schema before release.")
    if forecasts and not all("startTime" in row and "publishTime" in row and "generation" in row for row in forecasts[:10]):
        print("WARNING: one or more forecast rows do not contain the expected startTime/publishTime/generation fields.")
    print("\nVerification requests completed. Confirm field semantics, unit definitions, and whether the returned forecast vintage dates cover the required D−1 decision cutoff before marking the live integration as verified.")
    print(f"Check timestamp: {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
