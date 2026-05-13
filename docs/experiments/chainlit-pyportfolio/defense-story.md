# How To Explain The Current System

This is the shortest accurate story for the current active demo.

## One-sentence version

This system collects investor answers, calculates an investor profile,
checks liquidity needs, and then builds a sample portfolio inside the approved
limits for the final profile.

## The five-step story

1. The user answers the questionnaire in the chat.
2. The system saves the answers and shows a numbered review summary.
3. The system calculates one of five investor profiles:
   - `very_conservative`
   - `conservative`
   - `balanced`
   - `growth`
   - `aggressive`
4. The user can review that profile and override it during advisor review if needed.
5. The system checks whether the active profile can support the required Cash liquidity floor.
6. The portfolio engine chooses the exact mix of holdings inside the final limits.

## Who owns what

The team decides:

- the questionnaire
- the investor-band design
- the allocation ranges for each band
- the explanation wording

The SOC data layer provides:

- the asset universe
- per-asset expected return and other asset fields
- the covariance matrix

The portfolio library provides:

- the calculation step that picks asset weights once the policy is fixed

## What to say in a defense

Good short version:

"The current demo separates investor profiling from portfolio building. The
questionnaire calculates a draft profile first, liquidity is checked separately,
and the portfolio engine only chooses holdings inside the final profile's
allowed ranges."

Good longer version:

"We are not letting the portfolio engine decide what type of investor the user
is. The questionnaire scoring model calculates a draft profile from risk
capacity and risk tolerance answers. Advisor review can still override that
profile during the demo. Liquidity is checked separately as a Cash-floor
guardrail, and the portfolio engine only solves for holdings inside the final
approved ranges."

## What not to say

Do not say:

- "The AI decides the investor type."
- "The questionnaire score is the only suitability control."
- "PyPortfolioOpt figures out the right client profile."

Those statements are not true for the current active path.

## Honest current limitations

- advisor/manual profile override is still available in review mode
- the scoring model is rules-based and still needs final team/regulatory review before production use
- numeric amount inputs drive the Cash-floor liquidity check, but not the broader risk score
- narrative free-text items are still not implemented in the chat
- the demo uses saved local CSV snapshots by default, with live SOC API loading available through configuration
- the covariance matrix still needs in-memory PSD repair before optimization

## Short reference

If you only remember one line, remember this:

`answers -> calculated profile -> review/override -> liquidity check -> profile ranges -> optimizer -> recommendation`
