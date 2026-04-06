# Chainlit Chat Experiment

This folder is an exploratory chat shell for the current Variant B investor
workflow.

It is meant for:

- testing a chatbot-style question flow quickly
- checking whether structured questionnaire answers feel natural in dialogue
- testing the review/edit plus manual mock-band flow without touching the main frontend

It is **not** the final product UI.

## What it uses

- `backend/soc_advisor/`
- `config/questionnaires/v2.json`
- `config/portfolio/v2.json`
- `config/scoring/v3.json` as fallback only

## How to run

Recommended Windows path from the repo root:

1. Double-click `Setup Dev.cmd`
2. Double-click `Run Chainlit Experiment.cmd`
3. Open `http://localhost:8010` if the browser does not open by itself

## What it currently does

- asks the current DOCX-aligned single-choice questions one by one
- accepts answer numbers, option ids, or full option labels
- saves answers live through the exploratory backend session flow
- keeps a running numbered answer tracker in the right sidebar
- sends a review step before finalizing the result
- lets the user change answers with `change <question number>`
- lets the user choose a draft investor band with `band <band number>`
- returns the selected draft band plus a Variant B `PyPortfolioOpt` recommendation

## Current limitations

- no LLM extraction yet
- no connection to the React frontend yet
- the current chat demo uses manual mock band selection
- the portfolio engine still uses snapshot CSV data rather than live API pulls
- numeric and free-text DOCX questions are still deferred

## Where the full docs live

- `docs/experiments/chainlit-pyportfolio/`
