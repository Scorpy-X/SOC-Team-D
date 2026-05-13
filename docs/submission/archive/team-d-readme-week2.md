# SOC Team D Week 2 Submission Repository

This is the private Week 2 submission repository for SOC Team D.

It is curated for demo reliability and technical traceability. The repository
keeps the current frontend demo, the reusable SOC data-access package, the main
notebook-based evidence, exported data snapshots, and the current investor
questionnaire draft.

## Start Here

- Demo setup: [`Setup Demo.cmd`](Setup%20Demo.cmd)
- Demo launch: [`Run Demo.cmd`](Run%20Demo.cmd)
- Week 2 summary: [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)
- Questionnaire draft: [`docs/submission/Investor Questionnaire Draft - Week 2.pdf`](docs/submission/Investor%20Questionnaire%20Draft%20-%20Week%202.pdf)
- Technical evidence notebook: [`notebooks/api_tryouts.ipynb`](notebooks/api_tryouts.ipynb)
- Full asset-analysis notebook: [`notebooks/full_assets_df_analysis.ipynb`](notebooks/full_assets_df_analysis.ipynb)
- Browser-friendly notebook export: [`notebooks/api_tryouts.html`](notebooks/api_tryouts.html)
- Data evidence: [`data/exports/`](data/exports/)
- Problem framing note: [`docs/guides/problem-understanding.md`](docs/guides/problem-understanding.md)

## What This Submission Shows

- a working frontend advisory demo in `frontend/`
- a reusable Python SOC API package in `backend/soc_api/`
- notebook-based exploration of the challenge data
- exported asset, covariance, and correlation tables in `data/exports/`
- a cleaned Week 2 investor questionnaire draft in `docs/submission/`

## Current Demo Status

- the frontend demo currently uses mock recommendation data
- the demo does **not** require the Python backend
- the demo does **not** require an API key
- there is **no** separate `Run API.cmd` in this repo because this submission
  repo presents the backend honestly as a reusable Python package plus notebooks,
  not as a served application

## Demo Setup

### Quickest path

1. Double-click `Setup Demo.cmd`
2. Wait for setup to finish
3. Double-click `Run Demo.cmd`
4. Open `http://localhost:5173` if the browser does not open by itself

### Developer path

1. Double-click `Setup Dev.cmd`
2. Add your API key to `.env` only if you want live SOC API notebook work
3. In VS Code or Jupyter, select the kernel `Python 3.12 (SOC Team D)` for notebooks
4. Double-click `Run Demo.cmd` when you want the frontend

## Script Guide

- `Setup Demo.cmd`
  - checks Node/npm
  - installs frontend dependencies
  - falls back from `npm ci` to `npm install` on common Windows file-lock issues
  - does not set up Python
- `Setup Dev.cmd`
  - checks Python and Node/npm
  - creates `.venv`
  - installs `requirements.txt`
  - registers the notebook kernel `Python 3.12 (SOC Team D)`
  - installs frontend dependencies
  - creates `.env` from `.env.example` when missing
- `Run Demo.cmd`
  - starts the frontend demo server
  - opens the demo URL
- `scripts/bootstrap_env.py`
  - command-line bootstrap for the full developer setup
- `scripts/register_repo_kernel.py`
  - registers the repo-local Jupyter kernel used by the notebooks
- `scripts/start_demo.ps1`
  - PowerShell entrypoint behind `Run Demo.cmd`
- `scripts/start_frontend.ps1`
  - starts the frontend directly from a terminal

## Technical Evidence Kept In This Repo

- `backend/soc_api/raw.py`
  - direct API access and payload handling
- `backend/soc_api/frames.py`
  - dataframe conversion helpers for analysis work
- `notebooks/api_tryouts.ipynb`
  - main notebook used to explore and inspect the challenge data
- `notebooks/api_tryouts.html`
  - rendered notebook export for quick browser review
- `notebooks/full_assets_df_analysis.ipynb`
  - deeper asset-table analysis notebook kept as supporting technical evidence
- `data/exports/`
  - exported CSV/XLSX snapshots derived from the SOC data
- `frontend/CONTRACT.md`
  - current frontend request/response contract

## What Was Intentionally Left Out

- assignment brief files and internal drafting documents
- internal assistant or agent-only repo files
- exploratory backend scaffold work that belongs in `SOC exp`
- extra exploratory notebooks and support files that do not strengthen the Week 2 submission story

## Manual Setup

Use this only if the launcher scripts do not work on the machine:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend
npm.cmd ci
cd ..
```

If `npm.cmd ci` fails on a Windows file-lock error, retry with:

```powershell
cd frontend
npm.cmd install
cd ..
```

The `.env` file matters only for live SOC API notebook work. The frontend demo
path does not need an API key.

If a live API notebook returns `403 Forbidden`, the API key in `.env` is
invalid or outdated even if the notebook itself is fine.

If you want to import the Python package directly from another file in this
repo, add `backend` to `sys.path` first:

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "backend"))
from soc_api.frames import get_full_assets_df, get_asset_covariance_df
from soc_api.raw import get_assets_json
```
