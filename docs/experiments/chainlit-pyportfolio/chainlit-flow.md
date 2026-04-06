# Chainlit Flow

## High-level idea

The chat app is now a small real workflow with typed questionnaire inputs and a manual mock-band step.

It behaves like this:

1. the chat starts a backend assessment session
2. each answer is saved immediately
3. numeric currency answers are normalized and explicitly confirmed before save
4. the sidebar reads from saved backend state
5. the user reviews numbered answers and can change them by number
6. the user selects a draft investor band with `band <number>`
7. the final submit step runs Variant B allocation

## What happens on each stage

### Chat start

- Chainlit creates a new backend session
- the backend gives back a `session_id`
- the chat stores that `session_id`, workflow stage, and selected mock band

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
- the user can type:
  - `change 2`
  - `band 4`
  - `confirm`

### Submit step

When the user confirms:

- Chainlit sends the selected `mock_profile_band`
- the backend builds a mock profile from that selected band
- the backend keeps the captured numeric liquidity inputs on the session
- the backend loads `config/portfolio/v2.json`
- the backend builds band-only constraints
- the backend runs `PyPortfolioOpt`
- the backend stores the profile and recommendation on the session
- the chat renders the final summary

## API note

The submit endpoint now accepts an optional request body:

- `mock_profile_band`

If that field is provided, the backend uses the manual-band path.

If it is omitted, the backend can still use the older scored-questionnaire
fallback path.

## Current limits

- the active chat demo does not derive the band from answers yet
- the new numeric liquidity inputs are not yet fed into scoring or allocation
- the active policy path has no answer-based overlays
- true free-text narrative questions are still deferred
