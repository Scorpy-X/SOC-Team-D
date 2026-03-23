import { getOptionLabel } from "../data/profileFields";

export default function RecommendationSummaryPage({
  recommendation,
  submittedProfile,
  onViewBreakdown,
  onStartOver
}) {
  const assetClassMix = buildAssetClassMix(recommendation.portfolio);
  const whyItFits = buildWhyItFits(recommendation, submittedProfile);
  const riskLevel = recommendation.risk_profile.label;

  return (
    <main className="page results-layout">
      <header className="hero">
        <span className="eyebrow">Your Recommendation</span>
        <h1>You are a {recommendation.risk_profile.label} investor</h1>
        <p>{recommendation.explanation}</p>
      </header>

      <div className="summary-grid">
        <section className="section-card card">
          <h2>Why this fits you</h2>
          <ul className="fit-list">
            {whyItFits.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="section-card card">
          <h2>Key metrics</h2>
          <ul className="summary-list">
            <li>
              <span className="value-label">Expected return</span>
              <span className="value-strong">
                {formatPercent(recommendation.summary.expected_return)}
              </span>
            </li>
            <li>
              <span className="value-label">Risk level</span>
              <span className="value-strong">{riskLevel}</span>
            </li>
            <li>
              <span className="value-label">Volatility</span>
              <span className="value-strong">
                {formatPercent(recommendation.summary.volatility)}
              </span>
            </li>
          </ul>
        </section>
      </div>

      <section className="section-card card">
        <h2>Portfolio mix</h2>
        <p className="hint">
          This view groups the recommendation by asset class before showing the
          deeper holding-level breakdown.
        </p>
        <div className="mix-list">
          {assetClassMix.map((item) => (
            <div key={item.assetClass} className="mix-item">
              <span className="mix-label">{item.assetClass}</span>
              <span className="mix-weight">{item.weight}%</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section-card card">
        <h2>Ask the advisor</h2>
        <p>
          Conversational follow-up is planned next. This area will become the
          handoff point for question answering and recommendation explanation.
        </p>
        <div className="advisor-placeholder">
          <p className="hint">
            Coming next: ask why this mix was chosen, how it could be adjusted,
            or what trade-offs it makes.
          </p>
          <button className="button-secondary" type="button" disabled>
            Ask the advisor coming next
          </button>
        </div>
      </section>

      <div className="results-actions results-actions-wrap">
        <button className="button-secondary" type="button" disabled>
          Ask the advisor
        </button>
        <button className="button-secondary" type="button" onClick={onViewBreakdown}>
          View full breakdown
        </button>
        <button className="button-primary" type="button" onClick={onStartOver}>
          Edit profile
        </button>
      </div>
    </main>
  );
}

function buildAssetClassMix(portfolio) {
  if (!Array.isArray(portfolio)) {
    return [];
  }

  const groupedWeights = portfolio.reduce((totals, holding) => {
    const currentWeight = totals[holding.asset_class] || 0;
    totals[holding.asset_class] = currentWeight + holding.weight;
    return totals;
  }, {});

  return Object.entries(groupedWeights).map(([assetClass, weight]) => ({
    assetClass,
    weight
  }));
}

function buildWhyItFits(recommendation, submittedProfile) {
  const riskProfile = recommendation.risk_profile;
  const bullets = [
    `Your ${getOptionLabel("time_horizon", riskProfile.time_horizon).toLowerCase()} time horizon supports a ${riskProfile.label.toLowerCase()} recommendation.`,
    `Your liquidity need is ${getOptionLabel("liquidity_need", riskProfile.liquidity_need).toLowerCase()}, which shapes how cautious the mix should be.`,
    `Your main goal is ${getOptionLabel("primary_goal", riskProfile.primary_goal).toLowerCase()}, so the portfolio mix is designed around that priority.`
  ];

  if (submittedProfile?.risk_profile_inputs?.loss_comfort) {
    bullets[1] = `Your comfort with short-term losses is ${getOptionLabel("loss_comfort", submittedProfile.risk_profile_inputs.loss_comfort).toLowerCase()}, which helps set the recommendation's risk level.`;
  }

  return bullets;
}

function formatPercent(value) {
  return `${(value * 100).toFixed(0)}%`;
}
