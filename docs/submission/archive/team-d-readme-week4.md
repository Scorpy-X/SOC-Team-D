# SOC Team D Week 4 Submission Repository

This repo is our Week 4 submission snapshot.

It shows a chat-based investment advisor prototype. A user answers a short
questionnaire, reviews their responses, chooses a draft investor profile, and
then receives a sample portfolio with holdings and summary metrics.

Compared with the Week 3 snapshot, this version is easier to use and easier to
understand:

- the questionnaire now includes both multiple-choice questions and money amount questions
- money amounts are checked and confirmed before they are saved
- the system tries to use live SOC data first and falls back to the saved local dataset if the live source is unavailable
- the docs explain the system and its limits more clearly
- the automated checks cover more of the questionnaire and portfolio flow

Older Week 3 and Week 2 material is still kept in the repo as history, but it
is no longer the main story.

## Start Here

- Week 4 summary: [`docs/submission/week-4-summary.md`](docs/submission/week-4-summary.md)
- Week 4 snapshot note: [`docs/submission/chainlit-prototype-snapshot.md`](docs/submission/chainlit-prototype-snapshot.md)
- Prototype overview: [`docs/experiments/chainlit-pyportfolio/README.md`](docs/experiments/chainlit-pyportfolio/README.md)
- Historical Week 3 summary: [`docs/submission/archive/team-d-week3-summary.md`](docs/submission/archive/team-d-week3-summary.md)
- Historical Week 2 summary: [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)

## Main Demo Path

1. Double-click [`Setup Dev.cmd`](Setup%20Dev.cmd)
2. Double-click [`Run Chainlit Experiment.cmd`](Run%20Chainlit%20Experiment.cmd)
3. Open `http://localhost:8010` if the browser does not open by itself

This is the main Week 4 prototype path.

## What Someone Can Do In This Prototype

1. Answer the questionnaire in the chat.
2. Confirm any money amounts before they are saved.
3. Review the answers and change one if needed.
4. Choose a draft investor profile.
5. Receive a sample portfolio based on that profile.

## What This Submission Shows

- a working chat-based advisor prototype
- a backend that saves answers and produces a portfolio recommendation
- a data layer that can use live SOC data or a saved local copy
- clear documentation about how the system works and where its limits are
- automated tests for the questionnaire, submission flow, and portfolio output

## Important Current Limits

- the user still chooses the draft investor profile manually
- the system does not yet derive that profile automatically from the answers
- money amount questions are collected and reviewed, but they do not yet change the portfolio recommendation
- free-text narrative answers are still not part of the live prototype
- expected returns are model inputs, not promises

## Technical Note

Current active configuration:

- questionnaire: `config/questionnaires/v3.json`
- scoring fallback: `config/scoring/v4.json`
- portfolio policy: `config/portfolio/v2.json`

Main repo areas:

- `experiments/chainlit_chat/` for the chat-based prototype
- `backend/soc_advisor/` for questionnaire, session, and portfolio logic
- `backend/soc_api/` for SOC API and dataframe access
- `docs/experiments/chainlit-pyportfolio/` for explanation and methodology notes
- `tests/` for automated coverage

## Other Paths In The Repo

- [`Run API.cmd`](Run%20API.cmd)
  - starts the backend API and opens the docs page
- [`Setup Demo.cmd`](Setup%20Demo.cmd) and [`Run Demo.cmd`](Run%20Demo.cmd)
  - start the secondary frontend-only demo

The frontend demo is still useful, but it is no longer the main Week 4 repo
story.

## Historical Submission Material

Older material remains in the repo on purpose.

Use these when you need the earlier submission framing:

- [`docs/submission/archive/team-d-week3-summary.md`](docs/submission/archive/team-d-week3-summary.md)
- [`docs/submission/archive/team-d-week3-chainlit-snapshot.md`](docs/submission/archive/team-d-week3-chainlit-snapshot.md)
- [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)
- [`docs/submission/Investor Questionnaire Draft - Week 2.pdf`](docs/submission/Investor%20Questionnaire%20Draft%20-%20Week%202.pdf)
- [`docs/submission/archive/team-d-readme-week2.md`](docs/submission/archive/team-d-readme-week2.md)
