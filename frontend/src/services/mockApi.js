import baseRecommendation from "../data/mockRecommendation.json";
import {
  allowedProfileValues,
  getFieldByName,
  getOptionLabel,
  profileFields
} from "../data/profileFields";

const bandLabels = {
  conservative: "Conservative",
  balanced: "Balanced",
  growth: "Growth",
  aggressive: "Aggressive"
};

export function getMockRecommendation(profile) {
  return new Promise((resolve, reject) => {
    window.setTimeout(() => {
      try {
        validateProfile(profile);
        const band = classifyProfile(profile);
        const bandPreset = getBandPreset(band);

        const recommendation = {
          risk_profile: buildRiskProfile(profile, band),
          portfolio: bandPreset.portfolio,
          summary: bandPreset.summary,
          explanation: buildExplanation(profile, band)
        };

        resolve(recommendation);
      } catch (error) {
        reject(error);
      }
    }, 1200);
  });
}

function validateProfile(profile) {
  if (!profile || typeof profile !== "object") {
    throw new Error("A valid investor profile is required.");
  }

  profileFields.forEach((field) => {
    const fieldValue = profile[field.section]?.[field.name];

    if (!allowedProfileValues[field.name].includes(fieldValue)) {
      throw new Error("The submission payload is incomplete or invalid.");
    }
  });
}

function classifyProfile(profile) {
  const timeHorizon = getProfileValue(profile, "time_horizon");
  const liquidityNeed = getProfileValue(profile, "liquidity_need");
  const lossComfort = getProfileValue(profile, "loss_comfort");
  const primaryGoal = getProfileValue(profile, "primary_goal");
  const savingsBand = getProfileValue(profile, "savings_band");
  const experience = getProfileValue(profile, "investment_experience");
  const incomeBand = getProfileValue(profile, "monthly_income_band");
  const expensesBand = getProfileValue(profile, "monthly_expenses_band");

  if (
    timeHorizon === "less_than_1_year" ||
    (liquidityNeed === "very_likely" && lossComfort === "not_comfortable")
  ) {
    return "conservative";
  }

  let score = 0;

  score += getScore("time_horizon", timeHorizon);
  score += getScore("liquidity_need", liquidityNeed);
  score += getScore("loss_comfort", lossComfort);
  score += getScore("primary_goal", primaryGoal);
  score += getScore("savings_band", savingsBand);
  score += getScore("investment_experience", experience);

  const incomeScore = getScore("monthly_income_band", incomeBand);
  const expensesScore = getScore("monthly_expenses_band", expensesBand);
  const incomeBuffer = incomeScore - expensesScore;

  if (incomeBuffer >= 2) {
    score += 1;
  } else if (incomeBuffer <= -1) {
    score -= 1;
  }

  if (score <= -1) {
    return "conservative";
  }

  if (score <= 3) {
    return "balanced";
  }

  if (score <= 6) {
    return "growth";
  }

  return "aggressive";
}

function buildRiskProfile(profile, band) {
  return {
    label: bandLabels[band],
    band,
    life_stage: getProfileValue(profile, "life_stage"),
    employment_status: getProfileValue(profile, "employment_status"),
    monthly_income_band: getProfileValue(profile, "monthly_income_band"),
    monthly_expenses_band: getProfileValue(profile, "monthly_expenses_band"),
    savings_band: getProfileValue(profile, "savings_band"),
    primary_goal: getProfileValue(profile, "primary_goal"),
    time_horizon: getProfileValue(profile, "time_horizon"),
    liquidity_need: getProfileValue(profile, "liquidity_need"),
    loss_comfort: getProfileValue(profile, "loss_comfort"),
    investment_experience: getProfileValue(profile, "investment_experience")
  };
}

function buildExplanation(profile, band) {
  const bandLabel = bandLabels[band].toLowerCase();
  const goal = getOptionLabel("primary_goal", getProfileValue(profile, "primary_goal")).toLowerCase();
  const horizon = getOptionLabel("time_horizon", getProfileValue(profile, "time_horizon")).toLowerCase();
  const liquidity = getOptionLabel("liquidity_need", getProfileValue(profile, "liquidity_need")).toLowerCase();
  const lossComfort = getOptionLabel("loss_comfort", getProfileValue(profile, "loss_comfort")).toLowerCase();

  return `This mock recommendation leans ${bandLabel} because the submitted profile points to a ${goal} objective, a ${horizon} time horizon, ${liquidity} need for near-term access to the money, and ${lossComfort} with short-term losses.`;
}

function getProfileValue(profile, fieldName) {
  const field = getFieldByName(fieldName);
  return profile[field.section][field.name];
}

function getScore(fieldName, value) {
  const scoreMap = {
    monthly_income_band: {
      under_100000: 0,
      "100000_200000": 1,
      "200000_350000": 2,
      "350000_500000": 3,
      over_500000: 4
    },
    monthly_expenses_band: {
      under_50000: 0,
      "50000_100000": 1,
      "100000_200000": 2,
      "200000_350000": 3,
      over_350000: 4
    },
    savings_band: {
      under_100000: -1,
      "100000_500000": 0,
      "500000_1000000": 1,
      "1000000_3000000": 2,
      over_3000000: 3
    },
    primary_goal: {
      preserve_capital: -2,
      earn_income: -1,
      save_for_major_goal: 0,
      retirement: 1,
      grow_wealth: 2
    },
    time_horizon: {
      less_than_1_year: -2,
      "1_to_3_years": -1,
      "3_to_5_years": 1,
      "5_plus_years": 2
    },
    liquidity_need: {
      very_likely: -2,
      somewhat_likely: -1,
      unlikely: 2
    },
    loss_comfort: {
      not_comfortable: -2,
      somewhat_comfortable: 0,
      comfortable: 1,
      very_comfortable: 2
    },
    investment_experience: {
      none: -1,
      limited: 0,
      moderate: 1,
      strong: 2
    }
  };

  return scoreMap[fieldName]?.[value] ?? 0;
}

function getBandPreset(band) {
  const bandPresets = {
    conservative: {
      portfolio: [
        { ticker: "TBILLJMD", asset_class: "Cash", weight: 35 },
        { ticker: "PVAU", asset_class: "Fixed Income", weight: 40 },
        { ticker: "XEAK", asset_class: "Fund", weight: 15 },
        { ticker: "WBG", asset_class: "Equity", weight: 10 }
      ],
      summary: {
        expected_return: 0.07,
        volatility: 0.04,
        diversification_note:
          "This mock allocation leans toward capital preservation and liquidity with a smaller equity position."
      }
    },
    balanced: {
      portfolio: baseRecommendation.portfolio,
      summary: baseRecommendation.summary
    },
    growth: {
      portfolio: [
        { ticker: "TBILLJMD", asset_class: "Cash", weight: 10 },
        { ticker: "PVAU", asset_class: "Fixed Income", weight: 25 },
        { ticker: "WBG", asset_class: "Equity", weight: 35 },
        { ticker: "XEAK", asset_class: "Fund", weight: 30 }
      ],
      summary: {
        expected_return: 0.14,
        volatility: 0.11,
        diversification_note:
          "This mock allocation increases equity and fund exposure to support a longer-term growth objective."
      }
    },
    aggressive: {
      portfolio: [
        { ticker: "TBILLJMD", asset_class: "Cash", weight: 5 },
        { ticker: "PVAU", asset_class: "Fixed Income", weight: 15 },
        { ticker: "WBG", asset_class: "Equity", weight: 50 },
        { ticker: "XEAK", asset_class: "Fund", weight: 30 }
      ],
      summary: {
        expected_return: 0.17,
        volatility: 0.15,
        diversification_note:
          "This mock allocation accepts more short-term volatility in exchange for a stronger long-term growth tilt."
      }
    }
  };

  return bandPresets[band];
}
