# Chainlit Prototype Snapshot

This note explains what changed in the Week 4 Team D snapshot.

## What Was Brought In

The Week 4 snapshot brings over the latest version of the advisor prototype
from `SOC exp`, including:

- the updated questionnaire flow
- the new handling for money amount questions
- the current backend logic for saving answers and producing a portfolio
- the latest supporting tests
- the clearer explanation and architecture notes

## What Changed For A Reader Or Demo User

Compared with Week 3:

- the questionnaire feels more realistic because it now includes money amount questions
- money amounts are checked and confirmed before they are stored
- the system can use live SOC data when it is available and fall back to the saved local data when it is not
- the written explanation of the project is easier to follow

## What Was Replaced

The main Week 3 repo story was replaced because it no longer described the most
recent prototype accurately.

That includes:

- the root `README.md`
- the visible Week 3 submission summary
- the experiment overview docs that still described the older questionnaire and data-loading story

## What Was Kept

These were intentionally preserved:

- `frontend/`
- `notebooks/`
- `data/exports/`
- the frontend demo launchers
- Week 2 submission material
- archived Week 3 submission material

The older material is still useful as project history and evidence.

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

## Current Limits To Keep Stating

- the draft investor profile is still chosen manually
- the questionnaire does not yet assign the final profile automatically
- money amount answers do not yet change the portfolio recommendation
- free-text narrative answers are still deferred
- the system is still an exploratory prototype, not a finished production advisory product
