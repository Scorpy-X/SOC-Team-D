# Week 5 Submission Summary

## What This Repo Shows Now

This snapshot presents the chat-based advisor prototype with a stronger
post-recommendation explanation layer.

A user can:

- answer the questionnaire in the chat
- confirm money amounts before they are saved
- review and edit their answers
- choose a draft investor profile
- receive a short portfolio snapshot in the chatbot
- open a generated HTML portfolio report with the detailed portfolio explanation

The repo also includes a separate technical audit report for debugging and
defense.

## What Improved Since Week 4

- the final chatbot response is shorter and more user-friendly
- the detailed portfolio explanation now lives in a generated HTML report
- the user report uses more client-facing language instead of backend terms
- the report shows portfolio mix, investments, currency exposure, key estimates, concentration checks, and limitations
- the audit report preserves decision trace details and technical risk signals
- optional OpenAI support can rewrite report prose, with deterministic fallback if it is disabled or fails
- automated tests now cover report generation and OpenAI fallback behavior

## What Works In The Prototype

- the chat asks the current questionnaire
- dollar amounts such as `$50,000` are accepted and checked
- the minimum portfolio amount of `$25,000` is shown and enforced
- each confirmed answer is saved immediately
- the review screen numbers answers clearly and supports `change <question number>`
- the user can choose a draft investor profile with `band <band number>`
- the system returns a compact portfolio snapshot in chat
- local HTML user and audit reports are generated after submission

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
- [`backend/soc_advisor/reporting.py`](../../backend/soc_advisor/reporting.py)
- [`backend/soc_advisor/report_templates/user_report.html.j2`](../../backend/soc_advisor/report_templates/user_report.html.j2)

## Quick Reviewer Path

1. Run `Setup Dev.cmd`.
2. Run `Run Chainlit Experiment.cmd`.
3. Answer the questionnaire.
4. Confirm at least one money amount.
5. Edit one answer with `change <question number>`.
6. Choose a draft investor profile with `band <band number>`.
7. Confirm and inspect the final chatbot snapshot.
8. Open the attached/generated HTML portfolio report.
