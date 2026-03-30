# Chainlit Flow

This note describes the current Week 3 Chainlit flow in `SOC Team D`.

## High-level idea

The chat app is now a small real workflow with a manual mock-band step.

It behaves like this:

1. the chat starts a backend assessment session
2. each answer is saved immediately
3. the sidebar reads from saved backend state
4. the user reviews numbered answers and can change them by number
5. the user selects a draft investor band with `band <number>`
6. the final submit step runs Variant B allocation

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
- the live question set now uses the single-choice items from the DOCX that fit the current chat flow
- the answer is validated against the questionnaire config
- the backend saves the answer immediately
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
- the active policy path has no answer-based overlays
- numeric and free-text DOCX questions are still deferred
