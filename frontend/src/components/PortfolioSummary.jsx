function formatPercent(value) {
  return `${(value * 100).toFixed(0)}%`;
}

export default function PortfolioSummary({ summary }) {
  return (
    <section className="section-card card">
      <h3>Portfolio summary</h3>
      <ul className="summary-list">
        <li>
          <span className="value-label">Expected return</span>
          <span className="value-strong">{formatPercent(summary.expected_return)}</span>
        </li>
        <li>
          <span className="value-label">Volatility</span>
          <span className="value-strong">{formatPercent(summary.volatility)}</span>
        </li>
        <li>
          <span className="value-label">Diversification note</span>
          <span className="value-strong">{summary.diversification_note}</span>
        </li>
      </ul>
    </section>
  );
}
