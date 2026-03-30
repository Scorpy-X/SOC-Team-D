# Chainlit Prototype Snapshot

This note explains what was promoted into the Week 3 Team D snapshot.

## Promoted From SOC exp

- `backend/soc_advisor/`
- `config/`
- `experiments/chainlit_chat/`
- `.chainlit/`
- `public/chainlit-custom.css`
- `Run Chainlit Experiment.cmd`
- `Run API.cmd`
- `scripts/start_chainlit_experiment.ps1`
- `scripts/start_backend.ps1`
- `scripts/run_advisor_api.py`
- `requirements-chainlit.txt`
- `tests/`
- curated allocator and defense docs under `docs/experiments/chainlit-pyportfolio/`

## What Was Replaced

- the root `README.md`
- `requirements.txt`
- the developer bootstrap scripts that define the setup story

Those files had become out of date for the new Week 3 integrated prototype.

## What Was Preserved

- `frontend/`
- `notebooks/`
- `data/exports/`
- `Setup Demo.cmd`
- `Run Demo.cmd`
- Week 2 submission docs in `docs/submission/`

The Week 2 material still matters as historical evidence and should not be read
as if it vanished.

## Current Live Defaults

- questionnaire: `config/questionnaires/v2.json`
- scoring fallback: `config/scoring/v3.json`
- portfolio policy: `config/portfolio/v2.json`

## Current Product Truth

The active Team D prototype now does this:

1. capture questionnaire answers in Chainlit
2. save those answers in the backend session flow
3. allow review and numbered edits
4. let the user choose a manual mock band
5. allocate inside Variant B ranges using `PyPortfolioOpt`
6. return holdings, metrics, and active constraints

## Current Limits To Keep Stating

- manual mock band selection is still active
- question-to-band logic is not final
- covariance PSD repair is applied before optimization
- expected returns are estimates, not guarantees
- the allocator is still an exploratory prototype, not a production-approved advisory engine
