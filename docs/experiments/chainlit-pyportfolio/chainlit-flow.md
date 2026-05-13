# Chainlit Flow

## High-level idea

The chat app is now a small real workflow with typed questionnaire inputs, automatic profile scoring, advisor review, liquidity checking, and report generation.

It behaves like this:

1. the chat starts a backend assessment session
2. each answer is saved immediately
3. numeric currency answers are normalized and explicitly confirmed before save
4. the sidebar reads from saved backend state
5. the user reviews numbered answers and can change them by number
6. the system calculates an investor profile from the questionnaire
7. the user can override that profile with `band <number>` during advisor review
8. the user types `yes` to continue from review
9. the system checks whether the active profile can support the Cash liquidity floor
10. if needed, the system automatically moves to the nearest safer compatible profile and discloses that adjustment
11. the system shows an informational volatility notice
12. the user types `yes` again to generate the report
13. the final submit step runs the constrained allocation

## What happens on each stage

### Chat start

- Chainlit creates a new backend session
- the backend gives back a `session_id`
- the chat stores that `session_id`, workflow stage, and any advisor profile override

### Answering questions

- the user replies with:
  - option number
  - option id
  - or full option text
- for amount questions, the user can type a dollar amount such as `$50,000`
- the live question set now uses:
  - single-choice questions
  - numeric open-entry amount questions
- the answer is validated against the questionnaire config
- numeric amount answers are normalized and confirmed before save
- the backend saves the confirmed answer
- the sidebar updates from saved answers

### Review step

- once all questions are answered, the chat enters review mode
- the user sees numbered answers
- the review card highlights the profile calculated from the questionnaire
- the user can keep that calculated profile or choose an advisor/demo override
- the user can type:
  - `change 2`
  - `band 4` to override
  - `yes` to continue

### Submit step

When the user types `yes` from review:

- Chainlit submits the calculated profile unless the user selected an override
- the backend calculates the profile from `config/scoring/v5.json` or uses the advisor override
- the backend calculates the Cash liquidity floor from portfolio value, major expense need, monthly expenses, and emergency reserve months
- if the active profile cannot support that Cash floor, Chainlit automatically uses the nearest safer compatible profile and explains the adjustment
- if no configured profile can support the Cash floor, report generation is blocked and the user is returned to review
- Chainlit shows a volatility notice; only `yes` continues to report generation
- the backend loads `config/portfolio/v3.json`
- the backend builds profile constraints plus the Cash-floor liquidity overlay
- the backend runs `PyPortfolioOpt`
- the backend stores the profile and recommendation on the session
- the chat renders the final summary

## API note

The submit endpoint now accepts an optional request body:

- `mock_profile_band`

If that field is provided, the backend treats it as an advisor/demo override.

If it is omitted, the backend uses the calculated questionnaire profile.

## Current limits

- the broader suitability model is still under development
- liquidity inputs affect the Cash-floor compatibility check, not the normalized risk score
- the active policy path still avoids broader answer-based overlays beyond liquidity
- true free-text narrative questions are still deferred
