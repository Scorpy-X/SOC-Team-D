# How To Explain The Current System

This is the shortest accurate story for the current active demo.

## One-sentence version

This system captures investor answers, lets the user choose a draft investor
band manually, then uses a constrained optimizer to pick holdings inside that
band's allowed ranges.

## The five-step story

1. The user answers the current DOCX-aligned single-choice questionnaire.
2. The chat saves each answer immediately and shows a numbered review summary.
3. The user chooses one of five draft investor bands manually:
   - `very_conservative`
   - `conservative`
   - `balanced`
   - `growth`
   - `aggressive`
4. The portfolio config converts that band into allowed Cash, Fixed Income, and
   Equity ranges.
5. `PyPortfolioOpt` chooses the exact asset weights inside those allowed ranges
   using expected returns and covariance.

## Who owns what

The team owns:

- the questionnaire
- the investor-band design
- the allocation ranges for each band
- the explanation wording

The SOC data layer provides:

- the asset universe
- per-asset expected return and other asset fields
- the covariance matrix

`PyPortfolioOpt` provides:

- the numerical solver that picks asset weights once the band policy is fixed

## What to say in a defense

Good short version:

"The current demo separates suitability from allocation. The draft investor
band is selected first, and the optimizer only chooses holdings inside that
band's allowed ranges."

Good longer version:

"We are not letting the optimizer decide what type of investor the user is.
Right now the chat captures and reviews the questionnaire answers, then the
user selects a draft investor band manually while the question-to-band logic is
still being finalized. That band activates the Variant B class ranges, and
`PyPortfolioOpt` only solves for exact holdings inside those ranges."

## What not to say

Do not say:

- "The AI decides the investor type."
- "The questionnaire already determines the final band in the current demo."
- "PyPortfolioOpt figures out the right client profile."

Those statements are not true for the current active path.

## Honest current limitations

- the chat demo still uses manual mock band selection
- the old scoring config is retained only as a backend fallback
- numeric amount inputs from the DOCX are captured, but they do not yet drive allocation
- narrative free-text items are still not implemented in the chat
- the engine now tries live SOC API data first and falls back to local CSV snapshots
- the covariance matrix still needs in-memory PSD repair before optimization

## Short reference

If you only remember one line, remember this:

`answers -> review/edit -> manual band choice -> band ranges -> optimizer -> recommendation`
