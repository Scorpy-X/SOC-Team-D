import RiskProfileCard from "../components/RiskProfileCard";
import PortfolioTable from "../components/PortfolioTable";
import PortfolioSummary from "../components/PortfolioSummary";
import ExplanationPanel from "../components/ExplanationPanel";
import { getOptionLabel } from "../data/profileFields";

export default function ResultsPage({
  recommendation,
  submittedProfile,
  onBackToSummary,
  onStartOver
}) {
  return (
    <main className="page results-layout">
      <header className="hero">
        <span className="eyebrow">Full Breakdown</span>
        <h1>Detailed recommendation breakdown</h1>
        <p>
          This view keeps the richer profile and allocation detail for teammates
          who want to inspect the recommendation more closely.
        </p>
        {submittedProfile ? (
          <p className="hint">
            Submitted profile:{" "}
            {getOptionLabel(
              "life_stage",
              submittedProfile.personal_context.life_stage
            )}
            ,{" "}
            {getOptionLabel(
              "primary_goal",
              submittedProfile.investment_profile.primary_goal
            ).toLowerCase()}
            ,{" "}
            {getOptionLabel(
              "time_horizon",
              submittedProfile.investment_profile.time_horizon
            ).toLowerCase()}
            .
          </p>
        ) : null}
      </header>

      <div className="results-grid">
        <RiskProfileCard riskProfile={recommendation.risk_profile} />
        <PortfolioSummary summary={recommendation.summary} />
      </div>

      <PortfolioTable portfolio={recommendation.portfolio} />
      <ExplanationPanel explanation={recommendation.explanation} />

      <div className="results-actions">
        <button
          className="button-secondary"
          type="button"
          onClick={onBackToSummary}
        >
          Back to summary
        </button>
        <button className="button-secondary" type="button" onClick={onStartOver}>
          Edit Profile
        </button>
      </div>
    </main>
  );
}
