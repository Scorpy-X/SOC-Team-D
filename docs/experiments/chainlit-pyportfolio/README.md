# Chainlit Advisor And Portfolio Report Notes

This folder explains the active Week 6 advisor prototype in `SOC Team D`.

The live path is:

```text
typed questions -> money amount yes confirmation -> review/edit -> calculated profile -> optional advisor override -> liquidity check -> volatility notice -> yes -> allocation -> chat summary -> HTML reports
```

## What Someone Can Do

- answer the investor questionnaire in a chat window
- confirm parsed money amounts before they are saved
- review and edit numbered answers
- see the investor profile calculated from the questionnaire
- optionally choose a different profile during advisor/demo review
- have liquidity needs checked automatically before the report is generated
- see a disclosure if the profile is adjusted to support the required Cash reserve
- receive key portfolio metrics and grouped holdings in chat
- open a user-facing HTML portfolio report
- open a technical audit report for scoring, liquidity, formula, and optimizer trace details

## Most Useful Docs In This Folder

- `docx-aligned-risk-scoring.md` explains the question-to-profile model.
- `risk-profiling-questionnaire-reference.md` records the current questionnaire.
- `chainlit-flow.md` explains the chat flow.
- `deterministic-explanation-reference.md` lists the deterministic explanation wording.
- `testing-and-validation.md` explains the test and validation evidence.
- `optimizer-defense-and-validation.md` explains PyPortfolioOpt credibility and the SciPy cross-check.
- `pypfopt-constraints-to-holdings.md` explains how constraints become holdings.
- `portfolio-policy-matrix.md` summarizes the five profile constraints.
- `chainlit-house-ui.md` explains the Barita-leaning blue UI/report direction.
- `application-boundaries.md` explains where Chainlit, FastAPI, and PyPortfolioOpt fit.

## Active Configuration

- questionnaire: `config/questionnaires/v4.json`
- scoring: `config/scoring/v5.json`
- portfolio policy: `config/portfolio/v3.json`

## Main Files

- `experiments/chainlit_chat/chat_app.py`
- `backend/soc_advisor/`
- `backend/soc_advisor/report_templates/`
- `public/theme.json`
- `public/house-ui.css`
- `public/chainlit-custom.css`
- `public/elements/`
- `scripts/run_advisor_flow_validation.py`
- `scripts/run_optimizer_validation.py`
- `scripts/generate_sample_investor_reports.py`

## Important Boundary

This is the submitted Week 6 prototype path. It is not a final deployed client
portal and it is not final regulated financial advice. The purpose is to show a
working, explainable, testable advisor workflow that can be demonstrated and
defended.
