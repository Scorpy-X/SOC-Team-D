# Week 6 Submission Summary

## What This Snapshot Shows

This Week 6 snapshot presents the advisor prototype as a more explainable
investment workflow.

A user can:

- answer the investor questionnaire in the chat
- confirm money amounts before they are saved
- review and edit answers
- receive a calculated investor profile from questionnaire scoring
- optionally choose a different profile during advisor/demo review
- have liquidity needs checked before the portfolio is built
- see the profile automatically adjusted if the selected profile cannot support the Cash requirement
- review a volatility-based potential-loss notice
- receive a proposed portfolio in chat
- open a user-facing HTML report and a technical audit report

## Main Week 6 Improvements

- questionnaire answers now calculate the investor profile using the active scoring policy
- liquidity answers now affect the profile/portfolio through a Cash-floor compatibility check
- incompatible profiles are automatically adjusted to the nearest safer compatible profile
- the final chat response now shows key metrics and selected investments in a compact format
- sample user and audit reports can be generated for all five investor profiles
- the audit report now includes a chronological formula trail
- validation scripts now separately cover advisor decision flow and optimizer behavior
- the Chainlit review card uses a direct action callback for the risk-check step

## Active Configuration

- questionnaire: `config/questionnaires/v4.json`
- scoring: `config/scoring/v5.json`
- portfolio policy: `config/portfolio/v3.json`

## Validation Evidence

The snapshot includes:

- automated Python tests for questionnaire, scoring, liquidity, submission, reporting, portfolio construction, and validation scripts
- advisor-flow validation for calculated profiles, overrides, liquidity adjustment, blocking behavior, and risk trace persistence
- optimizer validation for every configured investor profile
- independent SciPy SLSQP replay of the constrained optimizer problem
- stress checks for return haircut, covariance shock, and largest-holding removal
- generated sample reports for visual review
- committed validation summaries and sample reports under `docs/submission/week-6-evidence/`

## Current Limits

- this remains a prototype, not final regulated financial advice
- expected returns are estimates, not promises
- the volatility notice is a simplified stress estimate, not a guaranteed maximum loss
- the questionnaire scoring policy is explainable, but final suitability logic still requires further approval
- OpenAI, when enabled, is only a prose assistant for report wording and cannot change recommendations

## Quick Reviewer Path

1. Run `Setup Dev.cmd`.
2. Run `Run Chainlit Experiment.cmd`.
3. Complete the questionnaire and confirm money amounts with `yes`.
4. Edit one answer from review to test the edit path.
5. Continue to the risk check.
6. Type `yes` after the volatility notice.
7. Open the generated portfolio report.
8. Run `Run Advisor Flow Validation.cmd`.
9. Run `Run Optimizer Validation.cmd`.
10. Run `Run Sample Investor Reports.cmd`.
