# Video demo script — maximum 10 minutes

**Recording status:** Script prepared. The actual video has not been recorded or uploaded. Record the running application in a network-enabled environment after validating Elexon responses and deploying the portal. Keep the uploaded YouTube video set to **Unlisted**, then test playback in an incognito window before submission.

## Before recording

- Start the production app or the local React/FastAPI services.
- Run `python scripts/verify_elexon.py` and confirm real source records are present.
- Open the application and `/docs` in separate tabs.
- Confirm the selected January day has real matched data; do not stage fake values.
- Close unrelated browser tabs and notifications. Use a 1920×1080 display if available.
- Keep the full video under 10 minutes. Part 1 and Part 2 must each be no longer than five minutes.

## Part 1 — customer pitch (0:00–4:50)

### 0:00–0:35 — The business problem

**Screen:** Overview page.

**Narration:** “A day-ahead purchasing decision has to be made before delivery, while wind output remains weather-dependent. The important question is not just what the final forecast turned out to be; it is what forecast was available at the decision deadline, and how reliable that forecast has historically been.”

### 0:35–1:25 — Decision-time view

**Screen:** Point to the evaluation period and the decision-cutoff selector. Set 09:00 and open Forecast explorer.

**Narration:** “The portal reconstructs the forecast vintage available at the chosen D−1 cutoff. For every half-hour it displays the forecast value, the actual value, the difference, and the publication time. Later revisions are not allowed to leak backward into the historical decision.”

### 1:25–2:15 — Inspect an interval

**Screen:** Choose a delivery date with good source coverage and hover the forecast/actual chart. Scroll the interval table to publication timestamps.

**Narration:** “The publication timestamp provides an audit trail for each selected forecast. If no forecast had been published by the cutoff, the record stays missing rather than being replaced with hindsight data.”

### 2:15–3:20 — Accuracy measures

**Screen:** Accuracy analysis, show MAE, RMSE, bias, WAPE and daily trend.

**Narration:** “MAE summarizes the average absolute miss; RMSE penalizes larger misses; bias shows whether the forecast tends to over- or underestimate output. WAPE gives a percentage scaled by total matched actual generation. We show all of these together because a small average bias can hide sizeable offsetting errors.”

### 3:20–4:10 — Coverage and limits

**Screen:** Overview coverage card and methodology page.

**Narration:** “Coverage matters. These metrics are calculated only for intervals with both forecast and actual data, and missing records remain visible. The pilot is intentionally limited to wind-generation information from Elexon; it does not claim to calculate exact residual demand, purchases, prices or savings.”

### 4:10–4:50 — Customer takeaway

**Screen:** Return to overview.

**Narration:** “The value of the pilot is a repeatable, auditable view of renewable forecast uncertainty at a chosen decision time. It gives the trading team a quantified starting point for evaluating wind uncertainty, while leaving procurement decisions to the utility’s full demand and market-position process.”

## Part 2 — internal technical review (5:00–9:50)

### 5:00–5:45 — Architecture

**Screen:** Show `docs/architecture.md`, then the directory layout.

**Narration:** “The frontend is React with TypeScript. FastAPI serves typed API routes and the production frontend. The Elexon HTTP client, timestamp selection logic, and metrics calculations are separate modules. There is no database because the first version is one historical month and uses a short in-memory cache.”

### 5:45–6:55 — Source integration and vintage logic

**Screen:** Open `backend/app/clients/elexon.py` and `backend/app/services/selection.py`.

**Narration:** “`startTime` identifies the delivery interval. `publishTime` tells us when the forecast became available. The selector converts the D−1 local deadline to UTC, then picks the latest publication at or before that instant. It joins by timestamp, not row order. If no eligible vintage exists, the forecast remains null.”

### 6:55–7:45 — Metric definitions

**Screen:** Open `backend/app/services/metrics.py` and show the tests.

**Narration:** “Metrics are computed from matched pairs only. MAE and RMSE are in MW; bias is forecast minus actual; WAPE is unavailable if the denominator is zero. Coverage uses the expected 1,488 January intervals, so incomplete source data does not disappear from the user’s view.”

### 7:45–8:35 — API and error states

**Screen:** `/docs`, then `/api/health` and the frontend's source-status/error state if reachable.

**Narration:** “The route layer validates date and cutoff parameters. The data client applies timeouts and bounded retries. The frontend has explicit loading and source-error states; it does not silently fall back to sample observations.”

### 8:35–9:20 — Docker and test workflow

**Screen:** Show `Dockerfile`, `docker-compose.yml`, `pytest` output and `npm run build` output.

**Narration:** “Compose starts separate frontend and backend services for local development. The production image builds the React bundle and serves it through FastAPI. The tests cover selection boundaries, missing-data behavior, metric formulas, endpoint parameters and API validation.”

### 9:20–9:50 — Limitations and handover

**Screen:** README limitations / API verification record.

**Narration:** “The decision cutoff is configurable but currently a pilot assumption. Before production, we need the trading desk’s actual deadline and a recorded verification of live Elexon historical-vintage responses. Exact procurement volume also needs demand and existing market-position data, which are deliberately outside this scope.”

## Upload and access check

1. Record the application and source walkthrough with a screen recorder.
2. Keep total runtime under 10 minutes; verify each part is within its limit.
3. Upload to YouTube and choose **Unlisted**.
4. Copy the genuine video URL into the submission README/form.
5. Open the URL in an incognito/private browser window and verify playback without signing in.
6. Repeat the incognito check for the deployed app and public repository.
