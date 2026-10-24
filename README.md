# Wind Forecast Intelligence Portal

A decision-support dashboard for comparing the UK national wind-generation forecast available before a day-ahead purchasing decision with subsequent actual generation. The default evaluation window is **1–31 January 2026**, using half-hourly observations from Elexon's `FUELHH` and `WINDFOR` datasets.

The portal reconstructs a decision-time forecast vintage instead of using hindsight: for each delivery interval it chooses the latest forecast publication whose `publishTime` is at or before the configured D−1 cutoff. Missing values stay missing and reduce the coverage score.

> **Data integrity note:** This workspace could not resolve `data.elexon.co.uk` while the application was being assembled, so a live data pull and upstream field verification could not be completed here. The integration uses the documented endpoints and includes a verification script. Run the verification steps below in a network-enabled environment before treating the data integration as production-verified. The application never substitutes synthetic observations for live source data.

## Features

- Executive view with MAE, RMSE, forecast bias, WAPE and interval coverage.
- Forecast-versus-actual trend and daily accuracy charts.
- Delivery-day explorer showing the selected publication timestamp for each half-hour.
- Decision cutoff selection for 09:00 and 15:00 UK time on D−1.
- Accuracy distribution and directional-error summaries.
- Data-source status, missing-data handling, CSV export and API documentation.
- React/TypeScript frontend, FastAPI backend and Docker-based workflows.

## Technology stack

- **Frontend:** React 18, TypeScript, Vite, Recharts, Lucide, Tailwind CSS.
- **Backend:** Python 3.12+, FastAPI, Pydantic, HTTPX.
- **Quality:** pytest, pytest-asyncio and Vitest/Testing Library.
- **Deployment:** Multi-stage Docker image, with a Heroku container deployment configuration.

## Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── clients/elexon.py          # Elexon HTTP client and response handling
│   │   ├── services/selection.py      # Timestamp normalization and forecast vintage selection
│   │   ├── services/metrics.py        # Accuracy metrics and daily aggregation
│   │   ├── services/data_service.py   # Retrieval, cache and dashboard assembly
│   │   ├── config.py                  # Environment-backed settings
│   │   ├── schemas.py                 # Shared Pydantic contracts
│   │   └── main.py                    # FastAPI endpoints and production SPA serving
│   ├── tests/                         # Unit and API validation tests
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/App.tsx                    # Main views and page state
│   ├── src/api.ts                     # Typed backend client/contracts
│   ├── src/format.ts                  # UK locale formatting helpers
│   ├── src/styles.css                 # Responsive product styling
│   ├── src/App.test.tsx
│   └── package.json
├── scripts/verify_elexon.py           # Live source-response verification
├── docs/architecture.md
├── docs/api-verification.md
├── docs/demo-script.md
├── Dockerfile                         # Multi-stage production image
├── docker-compose.yml                 # Local frontend/backend services
├── heroku.yml                         # Heroku container build configuration
└── .env.example
```

## Data sources

Only these two Elexon datasets supply observations and forecasts:

- Actual generation — [FUELHH stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
- Wind forecast publication vintages — [WINDFOR stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
- API developer portal and dataset retrieval guidance — [Elexon Insights Solution](https://developer.data.elexon.co.uk/)

The integration base URL is `https://data.elexon.co.uk/bmrs/api/v1`. Elexon documents public API access without an API key. Actuals are requested from `/datasets/FUELHH/stream` with settlement-date filters and `fuelType=WIND`. Forecast vintages are requested from `/datasets/WINDFOR/stream` using publication-time filters.

### Evaluation period and timestamps

The delivery period is UTC `[2026-01-01T00:00:00Z, 2026-02-01T00:00:00Z)`. It contains 1,488 expected half-hourly intervals. Publication retrieval includes 31 December 2025 through 30 January 2026 so the D−1 vintages for all January delivery dates can be selected.

API timestamps are normalized to aware UTC timestamps for matching. The decision cutoff is created in the `Europe/London` timezone on the calendar day before delivery and then converted to UTC. The default cutoff is 09:00 UK time; 15:00 is also available. These are explicit pilot assumptions and should be aligned with the client's confirmed trading desk deadline before operational use.

The `generation` field is handled as MW when provided by the documented dataset. MAE, RMSE and bias are MW. If interval energy is presented in an extension, a half-hourly average-power measure is converted using `MWh = MW × 0.5`; the current metrics report power error, not summed MW as energy.

### Metrics

For each matched pair, error is `forecast − actual`.

- **MAE:** mean absolute error, `mean(|forecast − actual|)`, in MW.
- **RMSE:** square root of mean squared error, in MW. Larger misses contribute more.
- **Bias:** `mean(forecast − actual)`, in MW. Positive means overforecast; negative means underforecast.
- **WAPE:** `sum(|error|) / sum(actual) × 100`. It is unavailable when the matched actual denominator is zero.
- **Coverage:** matched forecast/actual intervals divided by the 1,488 expected delivery intervals.

All error metrics use matched forecast/actual pairs. Missing values are not filled with zero and actual values are not forward-filled. Monthly metrics are computed from all matched intervals, not from an unweighted average of daily RMSE values.

## Run locally

### Option A: Docker Compose (recommended)

Prerequisite: Docker Engine/Desktop with Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs

The frontend's Vite server proxies `/api` calls to the backend container. The API will show an explicit source error if Elexon cannot be reached.

### Option B: Run backend and frontend separately

Prerequisites: Python 3.12+ and Node.js 20+.

Backend terminal:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend --port 8000
```

Frontend terminal:

```bash
cd frontend
npm install
npm run dev
```

### Verify Elexon before release

From the repository root:

```bash
pip install -r backend/requirements-dev.txt
python scripts/verify_elexon.py
```

The script prints the HTTP status, row count, field names and a bounded sample for each endpoint. Confirm the returned fields and actual/forecast units before marking live integration as verified. A successful empty response is not proof that the requested January history is present. Check that historical `publishTime` values cover the relevant D−1 cutoff dates and that each `startTime` represents the expected delivery interval.

The service caches a successful source snapshot in memory for 15 minutes by default. Change `CACHE_TTL_SECONDS` to tune this value. The first successful load fetches January actuals and daily forecast-publication windows from the preceding decision dates.

## Tests

Backend tests:

```bash
pytest
```

Frontend tests and production build:

```bash
cd frontend
npm install
npm test
npm run build
```

The backend test suite covers interval boundaries, D−1 cutoff generation, latest eligible forecast selection, exclusion of post-cutoff forecasts, missing values, duplicates, metric formulas, query parameters and API input validation. The actual upstream response shape is covered by the live verification script rather than a mocked test.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness check; does not contact Elexon |
| `GET /api/data-status` | Attempts source retrieval and reports row counts/status |
| `GET /api/dashboard?cutoff=09:00` | Monthly KPIs, daily trend, source counts and half-hourly series |
| `GET /api/forecast/day?date=2026-01-15&cutoff=09:00` | One delivery day's 48 intervals and metrics |
| `GET /api/accuracy?cutoff=09:00&start_date=2026-01-01&end_date=2026-01-31` | Aggregate metrics and daily trend for a January date range |
| `GET /api/export.csv?cutoff=09:00` | CSV of all January intervals, including missing-data statuses |

The server restricts delivery-date analysis to January 2026 and validates the cutoff as 24-hour `HH:MM` format. FastAPI's interactive schema is at `/docs` while the backend is running.

## Production Docker image

Build and run the combined production image (the frontend is built and served by FastAPI):

```bash
docker build -t wind-forecast-portal .
docker run --rm -p 8000:8000 wind-forecast-portal
```

Open http://localhost:8000. The image respects the hosting platform's `PORT` environment variable and serves `/api/*` through FastAPI, with the built frontend served for browser routes.

### Heroku deployment

Deployment has not been performed from this environment. With Heroku CLI authenticated and a public Git repository available, run commands similar to:

```bash
heroku login
heroku create <anonymous-app-name>
heroku stack:set container -a <anonymous-app-name>
git push heroku main
heroku open -a <anonymous-app-name>
```

Then verify the deployed `/api/health`, `/api/data-status`, frontend route, and CSV export in an unauthenticated/incognito browser. Save the confirmed application URL here after the check. Do not submit a URL based only on a successful build log.

### GitHub repository

Suggested anonymous repository name: `wvqjrn`. This is a suggested name only; a public repository has not been created from this environment.

```bash
git init
git add .
git commit -m "Build wind forecast intelligence portal"
gh repo create wvqjrn --public --source=. --remote=origin --push
```

Use a different available random name if `wvqjrn` is taken. Open the repository URL in an incognito browser and verify that the source and README are publicly accessible before submitting.

## Video and submission status

The timed recording plan is in [`docs/demo-script.md`](docs/demo-script.md). The actual unlisted YouTube video has not been recorded or uploaded from this environment. The video remains a required manual deliverable; do not treat the project as submission-complete until the video and public links have been checked in an incognito browser.

## Limitations and next steps

- The exact client decision deadline is not supplied; 09:00 UK time D−1 is a configurable default, not a client-confirmed trading rule.
- Live Elexon response verification remains outstanding in this artifact-authoring environment because DNS access to the upstream host failed. Run `python scripts/verify_elexon.py` from a network-enabled environment.
- This is an analysis portal, not an automated procurement optimizer. Customer demand, market prices, thermal fleet availability, existing purchases and monetary impact are intentionally not modelled.
- In-memory caching is per process; multiple production instances do not share a cache.
- The date range is intentionally restricted to January 2026.

## AI assistance and attribution

AI assistance: Claude was used to assist with implementation and testing. The developer is responsible for reviewing the code and verifying the data methodology and application behavior.

Data source: Elexon Insights Solution / BMRS. Retain Elexon attribution and comply with the applicable BMRS Data Licence Terms and API Terms of Use.
