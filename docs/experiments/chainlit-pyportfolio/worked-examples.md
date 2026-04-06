# Worked Examples

These examples reflect the **current** Variant B manual-band path.

They were generated from:

- `config/portfolio/v2.json`
- `full_assets_df.csv`
- `full_asset_covariance_df.csv`

## Very Conservative

- Class totals:
  - Cash `30.0%`
  - Fixed Income `66.3%`
  - Equity `3.7%`
- Top holdings:
  - `CWPU` `40.0%`
  - `TBILLJMD` `30.0%`
  - `PVAU` `26.3%`
- Summary metrics:
  - expected return `5.89%`
  - volatility `1.96%`

## Conservative

- Class totals:
  - Cash `20.0%`
  - Fixed Income `60.0%`
  - Equity `20.0%`
- Top holdings:
  - `CWPU` `40.0%`
  - `TBILLJMD` `20.0%`
  - `QPESE` `20.0%`
- Summary metrics:
  - expected return `7.59%`
  - volatility `3.21%`

## Balanced

- Class totals:
  - Cash `10.0%`
  - Fixed Income `50.0%`
  - Equity `40.0%`
- Top holdings:
  - `QPESE` `40.0%`
  - `TBILLJMD` `10.0%`
  - `CWPU` `10.0%`
- Summary metrics:
  - expected return `9.61%`
  - volatility `5.28%`

## Growth

- Class totals:
  - Cash `10.0%`
  - Fixed Income `30.0%`
  - Equity `60.0%`
- Top holdings:
  - `QPESE` `30.0%`
  - `XKFZ` `14.8%`
  - `BQB` `10.1%`
- Summary metrics:
  - expected return `10.62%`
  - volatility `7.23%`

## Aggressive

- Class totals:
  - Cash `0.0%`
  - Fixed Income `15.0%`
  - Equity `85.0%`
- Top holdings:
  - `XKFZ` `20.2%`
  - `BQB` `16.8%`
  - `QPESE` `15.0%`
- Summary metrics:
  - expected return `12.07%`
  - volatility `10.40%`

## Important takeaway

The current Variant B path is now producing portfolios that visibly separate
the bands. That is the main practical improvement over the older open-ended
guardrail policy.
