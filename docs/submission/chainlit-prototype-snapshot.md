# Chainlit Advisor Prototype Snapshot

This note records the Week 6 Chainlit advisor snapshot promoted into `SOC Team D`.

## What Was Brought In

The Week 6 snapshot brings in the current advisor/reporting system:

- questionnaire-driven investor profile scoring
- typed money amount capture with `yes` confirmation
- automatic liquidity compatibility check
- automatic adjustment to the nearest safer compatible profile when needed
- volatility notice before report generation
- constrained PyPortfolioOpt allocation using portfolio policy `v3`
- compact final chat summary with key metrics and grouped holdings
- user-facing HTML portfolio report
- technical audit report with decision trace and formula trail
- sample report generation for all five investor profiles
- advisor-flow and optimizer validation runners

## What Changed Since Week 5

Week 5 focused on generating user and audit reports after the chat result.

Week 6 moves the prototype further toward a defensible advisory workflow:

- the questionnaire now calculates the investor profile
- liquidity inputs now affect Cash reserve compatibility
- the system no longer treats liquidity as display-only
- profile adjustment is disclosed instead of hidden
- validation evidence is separated into advisor-flow validation and optimizer validation
- the README now explains scoring, liquidity, constraints, PyPortfolioOpt usage, and validation in one place

## Active Technical Configuration

- questionnaire: `config/questionnaires/v4.json`
- scoring: `config/scoring/v5.json`
- portfolio policy: `config/portfolio/v3.json`
- primary launcher: `Run Chainlit Experiment.cmd`
- validation launchers:
  - `Run Advisor Flow Validation.cmd`
  - `Run Optimizer Validation.cmd`
  - `Run Sample Investor Reports.cmd`

## What Was Kept

These areas were preserved as part of the curated submission:

- `frontend/`
- `notebooks/`
- `data/exports/`
- Week 2, Week 3, Week 4, and Week 5 submission material
- archived README and snapshot notes

Generated reports, validation logs, local databases, `.env`, virtual
environments, and temporary files are intentionally excluded.

## Current Limits To State Clearly

- this is still a prototype, not final regulated financial advice
- expected returns are estimates, not guarantees
- the volatility notice is a simple stress estimate, not a formal risk model
- final investment policy still needs wider review and approval
- optional OpenAI support is limited to prose rewriting only
