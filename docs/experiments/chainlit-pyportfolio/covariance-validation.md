# Covariance Validation

This note explains the two different checks that matter for the covariance
matrix in this project.

## The short version

- If you are comparing the saved CSV to the live API, you should expect an
  exact match.
- If you are rebuilding covariance from correlation plus `volatility_ann`, you
  should expect a very close match, but not necessarily a perfect one.

Those are not the same test.

## Why rebuilt covariance may differ slightly

The rebuilt path uses:

`covariance(i,j) = correlation(i,j) * volatility(i) * volatility(j)`

That reconstruction is mathematically valid, but it can differ slightly from
the saved covariance table because:

- the displayed correlation values may already be rounded
- the displayed volatility values may already be rounded
- multiplying rounded values can create tiny off-by-a-little differences

That is why a tolerance-based comparison is the right tool for the rebuilt
check.

## What we observed in the current data

On the current snapshot:

- the saved covariance CSV matches the live API covariance exactly
- the covariance rebuilt from correlation plus volatility is still extremely
  close to the saved matrix
- the largest rebuilt mismatch is tiny in absolute terms
- the matrix is symmetric
- the diagonal matches `volatility_ann^2` to near-machine precision

The remaining mismatch is consistent with small rounding or precision effects,
not with a broken export.

## Exact vs tolerance-based checks

### Exact check

Use exact equality when the question is:

- "did we export the API matrix correctly?"

That should be a hard yes/no check.

### Tolerance-based check

Use a tolerance-based comparison when the question is:

- "does the correlation/volatility data imply almost the same covariance?"

That should be measured with:

- maximum absolute difference
- mean absolute difference
- relative difference
- `numpy.allclose(...)` with reasonable tolerances

## Why "percentage closeness" is not the best main metric

A simple percent-closeness number sounds friendly, but it is not the most
reliable main test because:

- some matrix entries are very small, so percentages can look inflated
- zeros make percentage comparisons awkward
- optimization cares about numeric tolerance more than marketing-style
  "99.9% close" summaries

Percent-style summaries are still fine as supporting context, but the stronger
tests are absolute difference plus tolerance-based closeness.

## Re-run the check

Use:

```powershell
python scripts/check_covariance_consistency.py
```

If you want to avoid a live API call:

```powershell
python scripts/check_covariance_consistency.py --skip-live
```

If you want the full JSON report:

```powershell
python scripts/check_covariance_consistency.py --json
```
