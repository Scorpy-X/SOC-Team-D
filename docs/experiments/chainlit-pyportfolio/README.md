# Chat-Based Prototype Docs

This folder explains the current Week 4 advisor prototype in plain language.

At a high level, the prototype works like this:

1. the user answers a short questionnaire in a chat window
2. money amounts are checked and confirmed before they are saved
3. the user reviews the answers and can change one if needed
4. the user chooses a draft investor profile
5. the system produces a sample portfolio inside the limits for that profile

## What This Prototype Does

- runs a chat-based questionnaire
- accepts both multiple-choice answers and money amount answers
- saves answers as the conversation goes
- lets the user review numbered answers and update them by question number
- lets the user choose one of five draft investor profiles manually
- returns a sample portfolio with holdings, summary metrics, and policy limits

## What Is Important To Know

- the current demo still uses manual profile selection
- the questionnaire does not yet assign the final profile automatically
- money amount answers are collected and reviewed, but they do not yet change the portfolio recommendation
- free-text narrative answers are still not part of the live prototype
- the system tries to use live SOC data first and falls back to the saved local dataset if the live source is unavailable

## Read These First

1. `defense-story.md`
2. `risk-profiling-questionnaire-reference.md`
3. `application-boundaries.md`
4. `code-reading-guide.md`
5. `allocation-methodology-and-testing.md`
6. `pypfopt-constraints-to-holdings.md`
7. `portfolio-policy-matrix.md`
8. `chainlit-flow.md`
9. `worked-examples.md`

## Technical Note

Current active configuration:

- questionnaire: `config/questionnaires/v3.json`
- scoring fallback: `config/scoring/v4.json`
- portfolio policy: `config/portfolio/v2.json`

Main prototype files:

- `experiments/chainlit_chat/chat_app.py`
- `backend/soc_advisor/`
- `tests/`
