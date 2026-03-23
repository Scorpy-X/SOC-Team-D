import { getOptionLabel } from "../data/profileFields";

export default function RiskProfileCard({ riskProfile }) {
  const displayFields = [
    { label: "Life stage", name: "life_stage" },
    { label: "Employment status", name: "employment_status" },
    { label: "Primary goal", name: "primary_goal" },
    { label: "Time horizon", name: "time_horizon" },
    { label: "Liquidity need", name: "liquidity_need" },
    { label: "Loss comfort", name: "loss_comfort" },
    { label: "Investment experience", name: "investment_experience" },
    { label: "Savings band", name: "savings_band" }
  ];

  return (
    <section className="section-card card">
      <h2>Risk profile</h2>
      <p className="hint">
        This section reflects the submitted investor profile and the mocked
        four-band classification returned by the service layer.
      </p>
      <div className="profile-badge">{riskProfile.label}</div>

      <ul className="profile-list">
        {displayFields.map((field) => (
          <ProfileRow
            key={field.name}
            label={field.label}
            value={getOptionLabel(field.name, riskProfile[field.name])}
          />
        ))}
      </ul>
    </section>
  );
}

function ProfileRow({ label, value }) {
  return (
    <li>
      <span className="value-label">{label}</span>
      <span className="value-strong">{value}</span>
    </li>
  );
}
