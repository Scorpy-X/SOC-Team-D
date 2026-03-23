# Frontend Contract

This file defines the data shape the frontend sends and expects.

## Request shape

The profiling form submits this object through `src/services/api.js`:

```json
{
  "personal_context": {
    "life_stage": "mid_career",
    "employment_status": "full_time_employed"
  },
  "financial_profile": {
    "monthly_income_band": "200000_350000",
    "monthly_expenses_band": "100000_200000",
    "savings_band": "500000_1000000"
  },
  "investment_profile": {
    "primary_goal": "grow_wealth",
    "time_horizon": "5_plus_years",
    "liquidity_need": "unlikely"
  },
  "risk_profile_inputs": {
    "loss_comfort": "somewhat_comfortable",
    "investment_experience": "limited"
  }
}
```

## Response shape

The frontend expects this response structure:

```json
{
  "risk_profile": {
    "label": "Balanced",
    "band": "balanced",
    "life_stage": "mid_career",
    "employment_status": "full_time_employed",
    "monthly_income_band": "200000_350000",
    "monthly_expenses_band": "100000_200000",
    "savings_band": "500000_1000000",
    "primary_goal": "grow_wealth",
    "time_horizon": "5_plus_years",
    "liquidity_need": "unlikely",
    "loss_comfort": "somewhat_comfortable",
    "investment_experience": "limited"
  },
  "portfolio": [
    { "ticker": "TBILLJMD", "asset_class": "Cash", "weight": 15 }
  ],
  "summary": {
    "expected_return": 0.11,
    "volatility": 0.08,
    "diversification_note": "Exposure is spread across cash, fixed income, equity, and fund assets."
  },
  "explanation": "This mock recommendation reflects a balanced profile with a mix of stability and longer-term growth exposure."
}
```

## Mock classification bands

The mock backend currently assigns one of these four bands:

- `conservative`
- `balanced`
- `growth`
- `aggressive`

## Field meanings

- `ticker`: short identifier for the recommended asset.
- `asset_class`: broad category used to group the asset, such as `Cash`, `Fixed Income`, `Equity`, or `Fund`.
- `weight`: integer percentage of the portfolio allocation, not a decimal. Example: `25` means `25%`.
- `risk_profile.label`: user-facing title for the assigned mock band.
- `risk_profile.band`: machine-friendly version of the assigned mock band.

## Current source files

- Shared profile field metadata: `src/data/profileFields.js`
- Frontend service entrypoint: `src/services/api.js`
- Current mock backend behavior: `src/services/mockApi.js`
- Current mock payload base: `src/data/mockRecommendation.json`
