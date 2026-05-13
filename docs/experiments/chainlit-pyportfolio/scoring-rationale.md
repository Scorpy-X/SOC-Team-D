# Scoring Rationale

## Current Status

The active advisor flow now calculates an investor profile from the
questionnaire before the review step.

Current active files:

- questionnaire: `config/questionnaires/v4.json`
- scoring: `config/scoring/v5.json`
- portfolio policy: `config/portfolio/v3.json`

The detailed current scoring explanation lives in:

- `docs/experiments/chainlit-pyportfolio/docx-aligned-risk-scoring.md`

This file remains as a short orientation note so older references to “scoring
rationale” do not point to stale manual-band-first behavior.

## What The Active Scoring Path Does

`score_session()` in `backend/soc_advisor/services.py`:

1. reads the saved questionnaire answers
2. uses Q5-Q9 for risk capacity
3. uses Q10-Q14 for risk tolerance
4. normalizes each selected answer to a `0.0` to `1.0` score
5. calculates capacity and tolerance section scores using the DOCX-style weights
6. combines those section scores into one final score
7. maps that score into one of five investor profiles
8. applies the Q10 “sell everything” cap if needed
9. translates the final normalized score into a user-facing `1` to `10` risk score

The five investor profiles are:

- `very_conservative`
- `conservative`
- `balanced`
- `growth`
- `aggressive`

The `1` to `10` score is a display aid only. The underlying model still uses
the normalized `0.0` to `1.0` score and the five configured profile bands.

## Manual Override

The Chainlit review screen still lets the advisor/demo user choose a different
profile manually. That is now treated as an override, not the primary profile
calculation.

If no manual override is selected, the system uses the calculated questionnaire
profile.

## Liquidity Is Separate

Liquidity is not blended into the normalized risk score.

Instead, the liquidity questions are used before report generation to check
whether the selected profile can satisfy the required Cash allocation. If the
selected profile cannot hold enough Cash, the chatbot automatically uses the
nearest more conservative compatible profile and discloses that adjustment.

## Legacy Configs

Older additive scoring configs such as `config/scoring/v4.json` still exist for
historical compatibility and tests. They are not the active Week-current scoring
story.
