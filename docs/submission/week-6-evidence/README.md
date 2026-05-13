# Week 6 Validation Evidence Snapshot

This folder contains a small, committed evidence snapshot for reviewers who
want to inspect validation results without running the scripts locally.

The runtime output folders remain ignored:

- `data/validation/`
- `data/reports/`

Those folders are still used when the validation scripts and report generator
run. The files in this evidence folder are copied snapshots from a Week 6
validation run.

## Included Evidence

- `advisor-flow-validation-summary.txt`
  - Confirms the advisor flow scenarios passed.
  - Covers calculated profile submission, manual override behavior, liquidity
    adjustment, rejected unknown profiles, no-compatible-profile blocking, and
    risk-reality trace persistence.

- `optimizer-validation-summary.txt`
  - Confirms every active investor profile produced a feasible optimized
    portfolio.
  - Shows portfolio constraints, holdings, superclass totals, stress checks,
    and the independent SciPy SLSQP cross-check.

- `sample-balanced-user-report.html`
  - Example client-facing HTML portfolio report.
  - Shows the report layout, portfolio mix, metrics, grouped holdings,
    explanations, and limitations.

- `sample-balanced-audit-report.html`
  - Example internal technical audit report.
  - Shows the deeper trace: questionnaire scoring, liquidity calculation,
    risk notice, formulas, optimizer inputs, constraints, and report-generation
    details.

## What This Evidence Supports

This evidence supports the claim that the Week 6 prototype follows its
documented rules:

- questionnaire answers can produce an investor profile
- liquidity policy can adjust the effective profile when needed
- portfolio constraints are enforced for each investor type
- optimizer output can be replayed through an independent SciPy solver path
- generated reports contain both client-facing explanations and internal audit
  trace details

It does **not** prove that the portfolio is guaranteed suitable financial
advice. Expected returns remain estimates, and final regulated investment
policy would still require professional review.

## How To Regenerate

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\run_advisor_flow_validation.py
.\.venv\Scripts\python.exe scripts\run_optimizer_validation.py
.\.venv\Scripts\python.exe scripts\generate_sample_investor_reports.py
```

Or use the Windows launchers:

- `Run Advisor Flow Validation.cmd`
- `Run Optimizer Validation.cmd`
- `Run Sample Investor Reports.cmd`
