# VibeMoney Stock API (Scaffold)

A FastAPI service scaffold to serve stock data. This project currently exposes well-structured, dummy endpoints and a maintainable layout for future implementations.

## Features (scaffold only)
- Time series data by symbol and interval
- Quarterly fundamentals with release/filing dates
- Latest events/news for a symbol

## Project layout
```
app/
  api/
    v1/
      routers/
        latestevents.py
        quarterly.py
        timeseries.py
  core/
    config.py
  schemas/
    latestevents.py
    quarterly.py
    timeseries.py
  services/
    latestevents_service.py
    quarterly_service.py
    timeseries_service.py
  main.py
```

## Endpoints
- `GET /` — service metadata
- `GET /health` — health check
- `GET /api/v1/timeseries/{symbol}?interval=1d&limit=100`
- `GET /api/v1/quarterly/{symbol}`
- `GET /api/v1/latestevents?symbol=AAPL&limit=10`

All endpoints currently return empty payloads with the final response structure.

## Local development

Use the existing virtual environment under `.venv`.

### Install dependencies
```bash
. .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

### Run the API
```bash
. .venv/bin/activate
uvicorn app.main:app --reload
```

Open the docs at `http://localhost:8000/api/v1/docs`.

## Configuration
Environment variables are loaded via `pydantic-settings`. You can create a `.env` in the project root. See `app/core/config.py` for defaults.

## Next steps
- Implement service logic in `app/services/*` to fetch real data
- Add provider clients and error handling
- Add tests and CI
