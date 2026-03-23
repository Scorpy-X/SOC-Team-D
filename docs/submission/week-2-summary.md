# Week 2 Submission Summary

## What This Repo Delivers Now

- a working frontend demo for the investor profiling and recommendation flow
- a reusable Python package for retrieving and shaping SOC challenge data
- notebook-based technical evidence showing how the team explored the dataset
- exported tables for the asset universe, covariance, and correlations
- a cleaned investor questionnaire draft for the portfolio profiling workflow

## What Works In The Demo

- the user can open the frontend locally and complete the investor profile form
- the form submits through a stable frontend service boundary
- the demo returns a mock recommendation result with:
  - a risk profile label
  - a portfolio allocation
  - summary metrics
  - explanation text

## What Is Still Mocked Or In Progress

- the frontend currently uses mock recommendation logic rather than a live
  portfolio engine
- the questionnaire draft has been prepared as a submission artifact but is not
  yet wired into a backend questionnaire service in this repo
- the final portfolio logic, scoring, and dialogue layer are still under active
  team development

## Why The Backend Is Presented This Way

This submission repo does **not** include a separate API launcher.

That is intentional. For Week 2, the backend evidence in this repo is:

- the reusable `backend/soc_api/` package
- the notebook exploration flow
- the exported dataset artifacts

This keeps the submission honest and traceable instead of implying that a
served advisory backend already exists here when it does not.

## Technical Evidence To Review

- `notebooks/api_tryouts.ipynb`
- `notebooks/api_tryouts.html`
- `notebooks/full_assets_df_analysis.ipynb`
- `notebooks/full_assets_df_analysis.pdf`
- `data/exports/`
- `backend/soc_api/raw.py`
- `backend/soc_api/frames.py`
- `frontend/CONTRACT.md`
- `docs/guides/problem-understanding.md`

## Quick Reviewer Path

1. Run `Setup Demo.cmd`
2. Run `Run Demo.cmd`
3. Review the questionnaire draft in `docs/submission/`
4. Review the notebook HTML export and data exports for technical depth
