# Week 3 Submission Summary

## What This Repo Delivers Now

- a runnable Chainlit investor-advisor prototype
- an exploratory backend that persists questionnaire sessions and produces a
  Variant B portfolio recommendation
- the reusable SOC API/dataframe package from the earlier repo phase
- preserved notebook and export evidence from the Week 2 submission story
- documentation focused on defense, allocator methodology, and current limits

## Primary Week 3 Flow

The active prototype path is:

`questions -> review/edit -> manual mock band selection -> Variant B allocation -> holdings`

That means the Week 3 submission is no longer presenting the repo as only a
frontend mock demo. It now includes a runnable backend plus chat-driven
recommendation flow.

## What Works In The Prototype

- the user can answer the current DOCX-aligned single-choice questionnaire
- each answer is saved immediately in the backend session database
- the review screen numbers answers clearly and supports `change <question number>`
- the user can choose a draft investor band with `band <band number>`
- the backend applies Variant B class ranges from `config/portfolio/v2.json`
- `PyPortfolioOpt` returns holdings, metrics, active constraints, and notes
- the repo includes automated tests for submission, formatting, and portfolio feasibility

## What Is Still Honest Placeholder Work

- the current prototype still uses manual mock band selection
- question-to-band scoring is not yet the main demo path
- numeric and free-text questionnaire items are still deferred
- the allocator uses local snapshot CSVs instead of live runtime API pulls
- expected returns remain estimates, not guarantees
- the final scoring and policy rationale still need math-team approval

## Why The Repo Story Changed

Week 2 was intentionally conservative. It kept the repo centered on:

- the frontend mock demo
- the reusable SOC API package
- notebooks and exported evidence

Week 3 now promotes the integrated Chainlit/backend prototype because that is
the most meaningful new project progress since the earlier snapshot.

## Main Things To Review

- [`README.md`](../../README.md)
- [`docs/submission/chainlit-prototype-snapshot.md`](chainlit-prototype-snapshot.md)
- [`docs/experiments/chainlit-pyportfolio/README.md`](../experiments/chainlit-pyportfolio/README.md)
- [`docs/experiments/chainlit-pyportfolio/defense-story.md`](../experiments/chainlit-pyportfolio/defense-story.md)
- [`docs/experiments/chainlit-pyportfolio/allocation-methodology-and-testing.md`](../experiments/chainlit-pyportfolio/allocation-methodology-and-testing.md)

## Quick Reviewer Path

1. Run `Setup Dev.cmd`
2. Run `Run Chainlit Experiment.cmd`
3. Complete one questionnaire run
4. Edit one answer with `change <question number>`
5. Choose a draft band with `band <band number>`
6. Confirm and inspect the holdings and policy summary
