# Parallel29 Quote Smoke Bot

Lightweight Playwright script that fills out the full quote wizard on `https://www.parallel29.com/quote`, submits it, and validates success.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

```bash
source .venv/bin/activate
python quote_smoke_bot.py
```

The script passes when:
- `POST /api/quote` returns `200`
- the page shows `Request received.`

By default, each run randomizes:
- `contact_name` using your team-name list plus a random Pakistani caste
- `vehicle_year`, `vehicle_make`, and `vehicle_model` from common Pakistan-market cars
- U.S. `pickup_location` and `dropoff_location` from a lane pool
- `trailer_type` (`open` / `enclosed`)

## Useful options

```bash
python quote_smoke_bot.py --headful --screenshot artifacts/smoke-success.png
python quote_smoke_bot.py --reason dealership-transport --trailer-type enclosed
python quote_smoke_bot.py --contact-email smoketest+manual@example.com
python quote_smoke_bot.py --contact-name "Usama Lola Bhatti" --vehicle-make Toyota --vehicle-model Corolla --vehicle-year 2021
python quote_smoke_bot.py --pickup-location "Los Angeles, CA" --dropoff-location "Dallas, TX"
python quote_smoke_bot.py --runs 100 --concurrency 20
python quote_smoke_bot.py --runs 1000 --concurrency 100 --progress-every 25
python quote_smoke_bot.py --runs 100 --concurrency 20 --run-retries 3
```

If you override lane values, pass both `--pickup-location` and `--dropoff-location`.

## GitHub Actions

Workflow file: `.github/workflows/quote-smoke.yml`

- Manual run: **Actions -> Quote Smoke Test -> Run workflow**
- Manual inputs:
  - `runs` (default `10`)
  - `concurrency` (default `3`)
  - `progress_every` (default `10`)
  - `run_retries` (default `2`)
- Scheduled run: daily at `13:30 UTC` with defaults (`runs=3`, `concurrency=1`)

Workflow runs in `--skip-on-checkpoint` mode to avoid failing on Vercel anti-bot blocks from GitHub-hosted runners.
