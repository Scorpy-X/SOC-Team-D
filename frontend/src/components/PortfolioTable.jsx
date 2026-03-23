export default function PortfolioTable({ portfolio }) {
  if (!Array.isArray(portfolio) || portfolio.length === 0) {
    return (
      <section className="section-card card">
        <h2>Portfolio allocation</h2>
        <p className="hint">No portfolio allocation is available yet.</p>
      </section>
    );
  }

  return (
    <section className="section-card card">
      <h2>Portfolio allocation</h2>
      <div className="table-wrap">
        <table className="allocation-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Asset class</th>
              <th>Weight</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.map((holding) => (
              <tr key={holding.ticker}>
                <td>{holding.ticker}</td>
                <td>{holding.asset_class}</td>
                <td>
                  <span className="weight-pill">{holding.weight}%</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
