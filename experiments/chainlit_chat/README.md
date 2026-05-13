# Chainlit Chat Experiment

This folder contains the Chainlit chat app used for the Week 6 SOC advisor
prototype.

It is meant for:

- running the primary questionnaire-to-report demo
- testing a chatbot-style question flow quickly
- checking whether structured questionnaire answers feel natural in dialogue
- testing the review/edit/report handoff flow without touching the main frontend

It is the primary Week 6 demo UI, not a deployed client portal.

## What it uses

- `backend/soc_advisor/`
- `config/questionnaires/v4.json`
- `config/portfolio/v3.json`
- `config/scoring/v5.json`
- `public/elements/ReviewWorkspace.jsx`
- `public/elements/ReportReadyCard.jsx`

## How to run

Recommended Windows path from the repo root:

1. Double-click `Setup Dev.cmd`
2. Double-click `Run Chainlit Experiment.cmd`
3. Open `http://localhost:8010` if the browser does not open by itself

## What it currently does

- asks the current DOCX-aligned questionnaire one question at a time
- supports multiple-choice answers and confirmed money-amount answers
- accepts answer numbers or full answer labels for multiple-choice questions
- saves answers live through the exploratory backend session flow
- keeps a running `Assessment summary` in the right sidebar
- shows an interactive review workspace before finalizing the result
- lets the user edit answers from the review card or with `change <question number>`
- shows the profile calculated from the questionnaire
- lets the user override that profile from the review card or with `band <band number>`
- automatically adjusts to the nearest safer compatible profile if liquidity needs require more Cash
- blocks report generation if no configured profile can support the liquidity need
- shows an informational annual-volatility check before the user types `yes` to generate the report
- generates a short chat snapshot plus a detailed HTML portfolio report

Typed commands still work, but they are now the fallback path rather than the
primary user experience.

## Current limitations

- no connection to the React frontend yet
- manual profile selection is now an advisor/demo override, not the primary path
- numeric liquidity inputs drive the Cash-floor compatibility check, but not the broader suitability model
- no LLM extraction or narrative free-text interpretation yet
- the allocator uses saved CSV snapshots by default for reliable demos; live SOC data can be enabled through configuration

Internal note: the backend still uses Variant B portfolio constraints. Manual
profile override remains for advisor review, but calculated questionnaire
scoring is now the primary path.

## Where the full docs live

- `docs/experiments/chainlit-pyportfolio/`
