# SOC Team D Week 5 Submission Repository

This repo is our Week 5 submission snapshot.

It presents a chat-based investment advisor prototype. A user answers a short
questionnaire, reviews their responses, chooses a draft investor profile, and
receives a sample portfolio. The main Week 5 addition is that the prototype now
also generates a cleaner HTML portfolio report for the user and a separate
technical audit report for review and defense.

Compared with the Week 4 snapshot, this version is more report-ready:

- the chatbot final response is shorter and easier to scan
- the detailed portfolio explanation is moved into a local HTML report
- the user report uses more client-facing language, such as asset code and investment type
- the audit report keeps the technical decision trace and risk-signal details
- optional OpenAI support can rewrite report prose, but it cannot change holdings, metrics, profile selection, or allocation logic
- automated tests now cover report generation and OpenAI fallback behavior

Older Week 4, Week 3, and Week 2 material is still kept in the repo as history,
but it is no longer the main story.

## Start Here

- Week 5 summary: [`docs/submission/week-5-summary.md`](docs/submission/week-5-summary.md)
- Week 5 snapshot note: [`docs/submission/chainlit-prototype-snapshot.md`](docs/submission/chainlit-prototype-snapshot.md)
- Prototype overview: [`docs/experiments/chainlit-pyportfolio/README.md`](docs/experiments/chainlit-pyportfolio/README.md)
- Historical Week 4 summary: [`docs/submission/week-4-summary.md`](docs/submission/week-4-summary.md)
- Historical Week 3 summary: [`docs/submission/archive/team-d-week3-summary.md`](docs/submission/archive/team-d-week3-summary.md)
- Historical Week 2 summary: [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)

## Main Demo Path

1. Double-click [`Setup Dev.cmd`](Setup%20Dev.cmd)
2. Double-click [`Run Chainlit Experiment.cmd`](Run%20Chainlit%20Experiment.cmd)
3. Open `http://localhost:8010` if the browser does not open by itself

This is the main Week 5 prototype path.

## What Someone Can Do In This Prototype

1. Answer the questionnaire in the chat.
2. Confirm any money amounts before they are saved.
3. Review the answers and change one if needed.
4. Choose a draft investor profile.
5. Receive a short portfolio snapshot in the chatbot.
6. Open the generated HTML portfolio report for the detailed explanation.

The user report is generated locally under `data/reports/` during runtime. Those
generated files are intentionally not committed.

## What This Submission Shows

- a working chat-based advisor prototype
- a backend that saves answers and produces a portfolio recommendation
- local HTML report generation after recommendation
- a user-facing report with portfolio mix, investments, currency exposure, key estimates, and limitations
- a technical audit report with decision trace details
- a data layer that can use live SOC data or a saved local copy
- automated tests for questionnaire, submission, portfolio, report, and OpenAI fallback behavior

## Important Current Limits

- the user still chooses the draft investor profile manually
- the system does not yet derive that profile automatically from the answers
- money amount questions are collected and reviewed, but they do not yet change the portfolio recommendation
- free-text narrative answers are still not part of the live prototype
- expected returns are estimates, not promises
- generated reports are local artifacts, not a deployed client portal

## Technical Note

Current active configuration:

- questionnaire: `config/questionnaires/v3.json`
- scoring fallback: `config/scoring/v4.json`
- portfolio policy: `config/portfolio/v2.json`

Main repo areas:

- `experiments/chainlit_chat/` for the chat-based prototype
- `backend/soc_advisor/` for questionnaire, session, portfolio, and report logic
- `backend/soc_advisor/report_templates/` for the generated HTML reports
- `backend/soc_api/` for SOC API and dataframe access
- `docs/experiments/chainlit-pyportfolio/` for explanation and methodology notes
- `tests/` for automated coverage

Optional OpenAI report prose support is controlled by environment settings. It
is intentionally limited to prose rewriting only.

## Other Paths In The Repo

- [`Run API.cmd`](Run%20API.cmd)
  - starts the backend API and opens the docs page
- [`Setup Demo.cmd`](Setup%20Demo.cmd) and [`Run Demo.cmd`](Run%20Demo.cmd)
  - start the secondary frontend demo

The frontend demo is still useful, but it is not the main Week 5 repo story.

## Historical Submission Material

Older material remains in the repo on purpose.

Use these when you need earlier submission framing:

- [`docs/submission/week-4-summary.md`](docs/submission/week-4-summary.md)
- [`docs/submission/archive/team-d-readme-week4.md`](docs/submission/archive/team-d-readme-week4.md)
- [`docs/submission/archive/team-d-week4-chainlit-snapshot.md`](docs/submission/archive/team-d-week4-chainlit-snapshot.md)
- [`docs/submission/archive/team-d-week3-summary.md`](docs/submission/archive/team-d-week3-summary.md)
- [`docs/submission/archive/team-d-week3-chainlit-snapshot.md`](docs/submission/archive/team-d-week3-chainlit-snapshot.md)
- [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)
- [`docs/submission/Investor Questionnaire Draft - Week 2.pdf`](docs/submission/Investor%20Questionnaire%20Draft%20-%20Week%202.pdf)
- [`docs/submission/archive/team-d-readme-week2.md`](docs/submission/archive/team-d-readme-week2.md)
