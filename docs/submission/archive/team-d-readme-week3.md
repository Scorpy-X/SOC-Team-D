# SOC Team D Week 3 Submission Repository

This is the Week 3 submission snapshot for SOC Team D.

The repo now presents the current integrated prototype first:

`questionnaire -> review/edit -> manual mock band selection -> Variant B allocation -> holdings`

The older frontend-only Week 2 story is still preserved in
[`docs/submission/`](docs/submission/) and
[`docs/submission/archive/`](docs/submission/archive/), but it is no longer the
main repo identity.

## Start Here

- Week 3 summary: [`docs/submission/week-3-summary.md`](docs/submission/week-3-summary.md)
- Snapshot note: [`docs/submission/chainlit-prototype-snapshot.md`](docs/submission/chainlit-prototype-snapshot.md)
- Prototype docs: [`docs/experiments/chainlit-pyportfolio/README.md`](docs/experiments/chainlit-pyportfolio/README.md)
- Historical Week 2 summary: [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)
- Historical Week 2 README snapshot: [`docs/submission/archive/team-d-readme-week2.md`](docs/submission/archive/team-d-readme-week2.md)

## Primary Run Path

1. Double-click [`Setup Dev.cmd`](Setup%20Dev.cmd)
2. Double-click [`Run Chainlit Experiment.cmd`](Run%20Chainlit%20Experiment.cmd)
3. Open `http://localhost:8010` if the browser does not open by itself

This is the primary Week 3 prototype path.

## What This Week 3 Submission Shows

- a runnable Chainlit investor-advisor prototype in `experiments/chainlit_chat/`
- an exploratory backend allocator in `backend/soc_advisor/`
- a reusable SOC API package in `backend/soc_api/`
- the active questionnaire, scoring fallback, and Variant B policy configs in `config/`
- test coverage for submission and allocation behavior in `tests/`
- preserved frontend, notebook, and export evidence from the earlier repo story

## Current Active Prototype Flow

1. The chat asks the current DOCX-aligned single-choice questionnaire.
2. Each answer is saved immediately in the backend session store.
3. The user reviews numbered answers and can edit with `change <question number>`.
4. The user chooses a draft investor band with `band <band number>`.
5. The backend applies the Variant B class ranges from `config/portfolio/v2.json`.
6. `PyPortfolioOpt` selects exact holdings inside those band ranges using
   expected returns and covariance from the local snapshot data.

## Important Current Limits

- the current Week 3 prototype still uses **manual mock band selection**
- question-to-band scoring is **not** the primary demo path yet
- numeric and free-text DOCX questions are still deferred
- the portfolio engine uses local CSV snapshots rather than live runtime API pulls
- covariance PSD repair is applied before optimization
- expected returns are model inputs, not guarantees

## Primary And Secondary Launchers

- [`Setup Dev.cmd`](Setup%20Dev.cmd)
  - full developer setup
  - installs Python requirements, Chainlit extras, notebook tooling, and frontend dependencies
- [`Run Chainlit Experiment.cmd`](Run%20Chainlit%20Experiment.cmd)
  - primary Week 3 prototype launcher
- [`Run API.cmd`](Run%20API.cmd)
  - launches the exploratory backend API and opens FastAPI docs
- [`Setup Demo.cmd`](Setup%20Demo.cmd)
  - frontend-only setup path
- [`Run Demo.cmd`](Run%20Demo.cmd)
  - secondary frontend demo path

## Repo Areas To Review

- `backend/soc_advisor/`
  - current exploratory advisory backend and allocation engine
- `backend/soc_api/`
  - reusable SOC API/dataframe package
- `config/`
  - questionnaire `v2`, scoring fallback `v3`, portfolio policy `v2`
- `experiments/chainlit_chat/`
  - chat application for the Week 3 prototype
- `docs/experiments/chainlit-pyportfolio/`
  - defense, methodology, flow, and policy notes for the promoted prototype
- `tests/`
  - current automated coverage for submission, formatting, and Variant B behavior
- `frontend/`
  - preserved secondary demo surface
- `notebooks/`
  - technical evidence from data exploration
- `data/exports/`
  - snapshot data used by the allocator and notebooks

## Secondary Frontend Path

The React frontend is still present and still useful as evidence and demo
material, but it is no longer the first recommended repo story for Week 3.

If you only want the frontend demo:

1. Double-click [`Setup Demo.cmd`](Setup%20Demo.cmd)
2. Double-click [`Run Demo.cmd`](Run%20Demo.cmd)
3. Open `http://localhost:5173` if the browser does not open by itself

## Historical Submission Material

Week 2 material remains in the repo on purpose.

Use these when you need the earlier submission framing:

- [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)
- [`docs/submission/Investor Questionnaire Draft - Week 2.pdf`](docs/submission/Investor%20Questionnaire%20Draft%20-%20Week%202.pdf)
- [`docs/submission/archive/team-d-readme-week2.md`](docs/submission/archive/team-d-readme-week2.md)
- [`docs/submission/archive/team-d-snapshot-pre-week3.md`](docs/submission/archive/team-d-snapshot-pre-week3.md)
