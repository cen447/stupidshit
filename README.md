# Parallel29 Quote Smoke Bot

Lightweight Playwright script that fills out the full quote wizard on `https://www.parallel29.com/quote`, submits it, and validates success.

## Website

- GitHub Pages: `https://cen447.github.io/stupidshit/`
- Source page: `hawai_lullay_site.html`
- Deploy workflow: `.github/workflows/deploy-site.yml`
- Latest installer URLs:
- `https://github.com/cen447/stupidshit/releases/latest/download/parallel-smoke-latest-windows-setup.exe`
- `https://github.com/cen447/stupidshit/releases/latest/download/parallel-smoke-latest-macos.pkg`

## Native one-click installers (Windows + macOS)

This repo can now produce downloadable installers:

- Windows: `parallel-smoke-<version>-windows-setup.exe`
- macOS: `parallel-smoke-<version>-macos.pkg`

Where to download:

- GitHub Releases (for tagged versions like `v0.1.0`)
- Or workflow artifacts from **Actions -> Build Installers**

After install, open a new terminal and run from anywhere:

```bash
fuck asad 1
parallel-smoke --runs 1 --concurrency 1
```

Notes:
- macOS package is unsigned by default; Gatekeeper may prompt.
- First run may install Playwright Chromium automatically.

## One-command install (global command anywhere)

Mac/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/cen447/stupidshit/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/cen447/stupidshit/main/install.ps1 | iex
```

Then open a new terminal and run from any folder:

```bash
fuck asad 1
fuck asad 10
```

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

Quick terminal command:

```bash
./fuck asad 1
./fuck asad 10
```

Global CLI (after installer / pipx install):

```bash
fuck asad 1
parallel-smoke --runs 1 --concurrency 1
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
python quote_smoke_bot.py --runs 1 --run-retries 0 --checkpoint-grace-ms 10000 --ready-timeout-ms 30000
```

If you override lane values, pass both `--pickup-location` and `--dropoff-location`.

## GitHub Actions

Workflow file: `.github/workflows/quote-smoke.yml`

- Manual run: **Actions -> Quote Smoke Test -> Run workflow**
- Manual inputs:
  - `runs` (default `10`)
  - `concurrency` (default `3`)
  - `progress_every` (default `10`)
  - `run_retries` (default `0`)
- Scheduled run: daily at `13:30 UTC` with defaults (`runs=3`, `concurrency=1`)

Workflow is configured in strict mode: only real successful submissions pass; checkpoint blocks fail fast.

### Optional: allow authorized CI traffic via WAF rule

If your own WAF blocks GitHub runners, configure an explicit allow/bypass rule for smoke tests:

1. In Vercel Firewall/WAF, create a rule for paths `/quote` and `/api/quote`.
2. Add condition: request header `x-smoke-test-key` equals a secret value.
3. Set rule action to bypass/allow (for authorized test traffic only).
4. Add repo secret `SMOKE_BYPASS_HEADER_VALUE` in GitHub Actions.

The workflow sends this header automatically when the secret is set.
