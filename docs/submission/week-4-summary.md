# Week 4 Submission Summary

## What This Repo Shows Now

This snapshot presents a chat-based advisor prototype that can:

- collect questionnaire answers
- check and confirm money amounts before saving them
- let the user review and edit their answers
- let the user choose a draft investor profile
- produce a sample portfolio with holdings and summary metrics

It also includes supporting notes, saved data exports, notebooks, and automated
checks.

## What Improved Since Week 3

- the questionnaire is more realistic because it now includes both multiple-choice and money amount questions
- money amounts are not saved blindly; the user sees the interpreted value and confirms it
- the system can try live SOC data first and fall back to the saved local dataset if needed
- the project docs now explain the system in a clearer way for reviewers
- automated testing now covers more of the questionnaire and portfolio flow

## What Works In The Prototype

- the chat asks the current questionnaire
- dollar amounts such as `$50,000` are accepted and checked
- the minimum portfolio amount of `$25,000` is shown and enforced
- each confirmed answer is saved immediately
- the review screen numbers answers clearly and supports `change <question number>`
- the user can choose a draft investor profile with `band <band number>`
- the system returns holdings, summary metrics, and the active policy limits

## What Is Still Not Final

- the user still chooses the draft investor profile manually
- the system does not yet turn questionnaire answers into the final profile automatically
- money amount answers are collected, but they do not yet change the portfolio recommendation
- free-text narrative answers are still deferred
- expected returns remain estimates, not guarantees
- final policy reasoning still needs approval from the math side of the team

## Main Files To Review

- [`README.md`](../../README.md)
- [`docs/submission/chainlit-prototype-snapshot.md`](chainlit-prototype-snapshot.md)
- [`docs/experiments/chainlit-pyportfolio/README.md`](../experiments/chainlit-pyportfolio/README.md)
- [`docs/experiments/chainlit-pyportfolio/application-boundaries.md`](../experiments/chainlit-pyportfolio/application-boundaries.md)
- [`docs/experiments/chainlit-pyportfolio/risk-profiling-questionnaire-reference.md`](../experiments/chainlit-pyportfolio/risk-profiling-questionnaire-reference.md)

## Quick Reviewer Path

1. Run `Setup Dev.cmd`
2. Run `Run Chainlit Experiment.cmd`
3. Answer the questionnaire
4. Confirm at least one money amount
5. Edit one answer with `change <question number>`
6. Choose a draft investor profile with `band <band number>`
7. Confirm and inspect the final portfolio summary
