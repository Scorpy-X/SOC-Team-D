# Chainlit + PyPortfolio Prototype Docs

This folder documents the current active Week 4 prototype in `SOC Team D`.

The active flow is:

`typed questions -> numeric confirm where needed -> review/edit -> manual mock band selection -> Variant B allocation -> holdings`

## What This Week 4 Prototype Does

- runs a Chainlit chat UI
- uses the typed `v3` questionnaire with single-choice and numeric amount inputs
- saves questionnaire answers live into the exploratory backend SQLite database
- asks the user to confirm parsed currency amounts before saving them
- lets the user review numbered answers and change them by question number
- lets the user choose one of five draft investor bands manually
- applies the Variant B class ranges from `config/portfolio/v2.json`
- runs `PyPortfolioOpt` against live SOC data when available, with CSV snapshots as backup
- returns a portfolio recommendation with holdings, metrics, active constraints, and notes

## Current Truth

- the question-to-band pipeline is **not** the primary demo path yet
- the active demo path uses **manual mock band selection**
- the old scoring config still exists as a backend fallback, but it is not the main Week 4 story
- the active Variant B path has **no answer-based overlays**
- the active policy disallows `Fund` exposure for now
- numeric liquidity inputs are now captured and reviewable
- those numeric liquidity inputs are **not yet used** in the active scoring/allocation path
- true free-text narrative answers are still deferred

## Active Versions

- questionnaire: `config/questionnaires/v3.json`
- scoring fallback: `config/scoring/v4.json`
- portfolio policy: `config/portfolio/v2.json`

## Launch Path

For the main Week 4 prototype:

1. double-click `Setup Dev.cmd`
2. double-click `Run Chainlit Experiment.cmd`

## Read These First

1. `defense-story.md`
2. `risk-profiling-questionnaire-reference.md`
3. `application-boundaries.md`
4. `code-reading-guide.md`
5. `allocation-methodology-and-testing.md`
6. `pypfopt-constraints-to-holdings.md`
7. `portfolio-policy-matrix.md`
8. `chainlit-flow.md`
9. `worked-examples.md`
10. `data-usage.md`

## Main Prototype Files

- `experiments/chainlit_chat/chat_app.py`
- `backend/soc_advisor/`
- `config/questionnaires/v3.json`
- `config/portfolio/v2.json`
- `config/scoring/v4.json`
- `tests/`

## Important Boundary

This repo presents the Chainlit/backend path as the Week 4 integrated
prototype, but it is still an exploratory advisory system rather than a
finalized production product.

Keep stating the current limitations honestly:

- manual mock band selection is still active
- final question-to-band scoring is not final
- numeric amount inputs do not yet drive allocation
- covariance PSD repair is applied before optimization
- expected returns are estimates, not guarantees
