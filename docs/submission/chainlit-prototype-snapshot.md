# Chainlit Prototype Snapshot

This note explains what was promoted into the Week 4 Team D snapshot.

## Promoted From SOC exp

- updated `backend/soc_advisor/`
- updated `config/`
- updated `experiments/chainlit_chat/`
- current `tests/` and `pytest.ini`
- typed-answer support through `backend/soc_advisor/typed_answers.py`
- curated allocator and defense docs under `docs/experiments/chainlit-pyportfolio/`

## What Was Replaced

- the root `README.md`
- the visible Week 3 submission framing
- the Team D experiment docs that still described the older questionnaire/runtime story

Those files had become out of date for the new Week 4 integrated prototype.

## What Was Preserved

- `frontend/`
- `notebooks/`
- `data/exports/`
- `Setup Demo.cmd`
- `Run Demo.cmd`
- Week 2 submission docs in `docs/submission/`
- archived Week 3 repo-story material in `docs/submission/archive/`

The older submission material still matters as historical evidence and should
not be read as if it vanished.

## Current Live Defaults

- questionnaire: `config/questionnaires/v3.json`
- scoring fallback: `config/scoring/v4.json`
- portfolio policy: `config/portfolio/v2.json`

## Current Product Truth

The active Team D prototype now does this:

1. capture typed questionnaire answers in Chainlit
2. normalize and confirm numeric amount answers before saving
3. save those answers in the backend session flow
4. allow review and numbered edits
5. let the user choose a manual mock band
6. allocate inside Variant B ranges using `PyPortfolioOpt`
7. prefer live SOC data with CSV fallback
8. return holdings, metrics, active constraints, and notes

## Current Limits To Keep Stating

- manual mock band selection is still active
- question-to-band logic is not final
- numeric amount inputs do not yet drive allocation
- narrative free-text inputs are still deferred
- covariance PSD repair is applied before optimization
- expected returns are estimates, not guarantees
- the allocator is still an exploratory prototype, not a production-approved advisory engine
