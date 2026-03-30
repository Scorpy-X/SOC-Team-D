# Chainlit + PyPortfolio Prototype Docs

This folder documents the current active Week 3 prototype in `SOC Team D`.

The active flow is:

`questions -> review/edit -> manual mock band selection -> Variant B allocation -> holdings`

## What This Week 3 Prototype Does

- runs a Chainlit chat UI
- uses the current DOCX-aligned single-choice questionnaire subset
- saves questionnaire answers live into the exploratory backend SQLite database
- lets the user review numbered answers and change them by question number
- lets the user choose one of five draft investor bands manually
- applies the Variant B class ranges from `config/portfolio/v2.json`
- runs `PyPortfolioOpt` against the local CSV snapshots in `data/exports/`
- returns a portfolio recommendation with holdings, metrics, and active constraints

## Current Truth

- the question-to-band pipeline is **not** the primary demo path yet
- the active demo path uses **manual mock band selection**
- the old scoring config still exists as a backend fallback, but it is not the
  main Week 3 story
- the active Variant B path has **no answer-based overlays**
- the active policy disallows `Fund` exposure for now
- numeric and free-text DOCX items are still deferred

## Active Versions

- questionnaire: `config/questionnaires/v2.json`
- scoring fallback: `config/scoring/v3.json`
- portfolio policy: `config/portfolio/v2.json`

## Launch Path

For the main Week 3 prototype:

1. double-click `Setup Dev.cmd`
2. double-click `Run Chainlit Experiment.cmd`

## Read These First

1. `defense-story.md`
2. `allocation-methodology-and-testing.md`
3. `pypfopt-constraints-to-holdings.md`
4. `portfolio-policy-matrix.md`
5. `chainlit-flow.md`
6. `worked-examples.md`

## Main Prototype Files

- `experiments/chainlit_chat/chat_app.py`
- `backend/soc_advisor/`
- `config/questionnaires/v2.json`
- `config/portfolio/v2.json`
- `config/scoring/v3.json`
- `tests/`

## Important Boundary

This repo now presents the Chainlit/backend path as the Week 3 integrated
prototype, but it is still an exploratory advisory system rather than a
finalized production product.

Keep stating the current limitations honestly:

- manual mock band selection is still active
- final question-to-band scoring is not final
- covariance PSD repair is applied before optimization
- expected returns are estimates, not guarantees
