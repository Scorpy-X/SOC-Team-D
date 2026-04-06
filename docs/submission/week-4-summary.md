# Week 4 Submission Summary

## What This Repo Delivers Now

- a runnable Chainlit investor-advisor prototype with typed questionnaire inputs
- an exploratory backend that persists sessions and produces a Variant B portfolio recommendation
- a reusable SOC API/dataframe package for live and snapshot-backed data access
- stronger architecture, explainability, and questionnaire-reference docs
- expanded automated tests for typed answers, question flow, submission, and portfolio behavior
- preserved notebook, export, and frontend evidence from the earlier submission story

## Primary Week 4 Flow

The active prototype path is now:

`typed questions -> numeric confirm where needed -> review/edit -> manual mock band selection -> Variant B allocation -> holdings`

That means Week 4 is no longer just the Week 3 flow with minor cleanup. The
prototype now captures the numeric liquidity inputs, confirms them explicitly,
and uses the newer advisor defaults.

## What Works In The Prototype

- the user can answer the typed `v3` questionnaire
- dollar-amount questions accept values like `$50,000` and require explicit confirmation
- the `$25,000` portfolio minimum is shown and enforced
- each answer is saved immediately in the backend session database
- the review screen numbers answers clearly and supports `change <question number>`
- the user can choose a draft investor band with `band <band number>`
- the backend applies Variant B class ranges from `config/portfolio/v2.json`
- `PyPortfolioOpt` returns holdings, metrics, active constraints, and notes
- the allocator prefers live SOC API data and falls back to local CSV snapshots when needed

## What Is Still Honest Placeholder Work

- the current prototype still uses manual mock band selection
- question-to-band scoring is not yet the main demo path
- numeric amount inputs are captured but not yet fed into allocation
- narrative free-text questionnaire items are still deferred
- expected returns remain estimates, not guarantees
- the final scoring and policy rationale still need math-team approval

## Why The Repo Story Changed Again

Week 3 promoted the integrated Chainlit/backend prototype into Team D.

Week 4 keeps that same primary story, but now adds the more realistic typed
questionnaire handling, clearer system-boundary docs, and the live-primary
runtime data path that better reflects the current exploratory advisor stack.

## Main Things To Review

- [`README.md`](../../README.md)
- [`docs/submission/chainlit-prototype-snapshot.md`](chainlit-prototype-snapshot.md)
- [`docs/experiments/chainlit-pyportfolio/README.md`](../experiments/chainlit-pyportfolio/README.md)
- [`docs/experiments/chainlit-pyportfolio/application-boundaries.md`](../experiments/chainlit-pyportfolio/application-boundaries.md)
- [`docs/experiments/chainlit-pyportfolio/risk-profiling-questionnaire-reference.md`](../experiments/chainlit-pyportfolio/risk-profiling-questionnaire-reference.md)

## Quick Reviewer Path

1. Run `Setup Dev.cmd`
2. Run `Run Chainlit Experiment.cmd`
3. Enter valid answers for the typed questionnaire
4. Confirm at least one numeric amount answer
5. Edit one answer with `change <question number>`
6. Choose a draft band with `band <band number>`
7. Confirm and inspect the holdings and policy summary
