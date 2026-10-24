# Elexon API verification record

## Documented interface

The integration is configured for the documented Elexon base URL:

`https://data.elexon.co.uk/bmrs/api/v1`

- Actuals: `GET /datasets/FUELHH/stream` with `settlementDateFrom`, `settlementDateTo`, and `fuelType=WIND`.
- Historical forecast publications: `GET /datasets/WINDFOR/stream` with `publishDateTimeFrom` and `publishDateTimeTo`.

References:

- https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream
- https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream
- https://developer.data.elexon.co.uk/

Elexon's developer portal explains that dataset endpoints support querying publication times and retrieving superseded data, including historical forecasts. The specific response shape, field coverage for the selected dates, query-window behavior, and actual upstream response have **not been live-verified from this build environment**.

## Run the verification probe

```bash
pip install -r backend/requirements-dev.txt
python scripts/verify_elexon.py
```

The script makes two real calls for small, known periods, prints the response status, record count, record fields and a short sample, and exits non-zero if a call fails or a response cannot be normalized.

Before marking the integration verified, inspect:

1. Whether `FUELHH` returns `startTime`, `generation`, and the `WIND` category for the requested settlement date.
2. Whether actual values are average power in MW and whether duplicate revisions occur.
3. Whether `WINDFOR` returns `startTime`, `publishTime`, and `generation` for the target publication-time window.
4. Whether query end boundaries are inclusive or exclusive and whether adjacent daily queries may duplicate a boundary record.
5. Whether D−1 publication-time queries return all forecast vintages needed to reconstruct the selected cutoffs for every January target interval.
6. Whether returned forecast target timestamps line up with the FUELHH interval starts.

Do not mark this record complete until a successful run is saved with the verified response behavior. An HTTP 200 response with zero records is not enough to conclude that the historical evaluation data is available.
