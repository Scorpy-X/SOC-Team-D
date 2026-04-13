# Chainlit Prototype Snapshot

This note explains what changed in the Week 5 Team D snapshot.

## What Was Brought In

The Week 5 snapshot brings over the latest advisor/reporting work from
`SOC exp`, including:

- local HTML report generation after Chainlit submission
- a polished user-facing portfolio report
- a technical audit report with decision trace details
- optional OpenAI-assisted prose rewriting with deterministic fallback
- a shorter final chatbot response that points to the detailed report
- updated tests for report generation and report prose fallback behavior

## What Changed For A Reader Or Demo User

Compared with Week 4:

- the chatbot no longer tries to show every detail in the final message
- the user receives a cleaner HTML report for the detailed portfolio explanation
- report wording is more client-facing, using terms such as asset code and investment type
- technical details such as sensitivity values are kept in the audit report instead of the user report
- generated reports are saved locally under `data/reports/`

## What Was Replaced

The main Week 4 repo story was replaced because it did not describe the new
reporting layer.

That includes:

- the root `README.md`
- the visible submission summary
- this prototype snapshot note
- the experiment overview docs that still described the older chat-only final output

## What Was Kept

These were intentionally preserved:

- `frontend/`
- `notebooks/`
- `data/exports/`
- the frontend demo launchers
- Week 2 submission material
- archived Week 3 and Week 4 submission material

The older material remains useful as project history and evidence.

## Current Technical Note

Current active configuration:

- questionnaire: `config/questionnaires/v3.json`
- scoring fallback: `config/scoring/v4.json`
- portfolio policy: `config/portfolio/v2.json`

Current live behavior:

1. collect questionnaire answers in the chat
2. confirm money amounts before saving them
3. let the user review and edit answers
4. let the user choose a draft investor profile
5. build a sample portfolio inside the allowed policy ranges
6. generate a user HTML report and a technical audit report

## Current Limits To Keep Stating

- the draft investor profile is still chosen manually
- the questionnaire does not yet assign the final profile automatically
- money amount answers do not yet change the portfolio recommendation
- free-text narrative answers are still deferred
- the system is still an exploratory prototype, not a finished production advisory product
- OpenAI, when enabled, is only a prose assistant and does not make portfolio decisions
