# Architecture and technical review

## Overview

The application uses a small three-part structure: React/TypeScript for presentation, FastAPI for the HTTP/API boundary, and focused Python modules for Elexon retrieval and the forecast/actual calculations. There is no database or background worker because the first-version scope is a fixed historical month and the API data volume can be cached briefly in process memory.

```text
Browser
  │
  ├── React + Vite (development) / static React build (production)
  │       ├── typed API client
  │       ├── overview charts and KPI cards
  │       ├── half-hourly forecast explorer
  │       └── accuracy + methodology views
  │
  └── FastAPI
          ├── API routes + validation
          ├── WindDataService (short-lived snapshot cache)
          ├── ElexonClient (HTTP, retries, response validation)
          └── domain services
                  ├── selection.py (time normalization and vintage selection)
                  └── metrics.py (error metrics and daily grouping)
```

## Data flow

1. The backend requests `FUELHH` actual generation for the supported month and historical `WINDFOR` forecast rows filtered by publication time. Requests are split into smaller time windows to avoid a large single response.
2. A successful source snapshot is kept in memory for `CACHE_TTL_SECONDS` (15 minutes by default). Errors are surfaced and are not cached as successful data.
3. Timestamps are converted to UTC-aware `datetime` values. An absent timezone in a source timestamp is interpreted as UTC; this assumption should be rechecked if a source schema says otherwise.
4. For each half-hour delivery timestamp, the code derives the D−1 deadline in `Europe/London`, selects the most recent forecast publication no later than that deadline, and joins actual generation by the normalized delivery timestamp.
5. Metrics are computed from matched pairs; expected interval count and source/forecast coverage counts preserve the effect of gaps.
6. API routes serialize timestamps to ISO format with a `Z` suffix. The frontend only formats/visualizes responses; it does not independently recalculate accuracy metrics.

## Deliberate choices

- **No database:** the scope is a one-month evaluation and a simple expiring process-local cache is enough for the MVP. Persistent shared caching is a future improvement for multi-instance deployment.
- **UTC for matching:** timestamps represent absolute instants; UTC avoids string-format and local-time mismatches.
- **UK local time for the cutoff:** the commercial decision deadline is a local calendar rule. `zoneinfo` keeps the logic correct across DST boundaries.
- **Missing remains missing:** imputing zero generation or forward-filling forecasts would distort error metrics and imply information that the source did not supply.
- **No post-deadline forecast vintage:** this avoids look-ahead bias in a retrospective decision-time evaluation.
- **Data errors are explicit:** the UI indicates source unavailability and does not insert example values into a live dashboard.

## Operational notes

- `GET /api/health` is a liveness check, not a source-data check.
- `GET /api/data-status` performs/reuses a source snapshot retrieval and reports source record counts.
- `/docs` exposes the FastAPI OpenAPI interface.
- In development, Vite proxies `/api` to the backend container. In production, the final Docker image serves the Vite build using FastAPI static-file fallback.
- The production image relies on the `PORT` variable provided by the host.

## Limitations

The API base URL and dataset route patterns are based on Elexon's published documentation, but live responses could not be fetched from the current build environment. The included verification script must be run with network access before the result is presented as an end-to-end data-verified system. It is also necessary to confirm the client's true decision cutoff and whether its business process uses a single daily cutoff or market-specific cutoffs.
